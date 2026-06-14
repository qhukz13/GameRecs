from __future__ import annotations

import json
from typing import Any
import logging

import requests

from app.application.services.vector_math import normalize
from app.core.config import settings
from app.domain.entities import ReviewAnalysis
from app.application.services.ai_service import AIService


class BaseLLMProvider:
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError()

    def analyze_review(self, review_text: str, rating: int) -> ReviewAnalysis:
        raise NotImplementedError()

    def explain_recommendation(self, game: Any, score: float, group_features: list[str] | None = None) -> str:
        raise NotImplementedError()


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        self.model = model or settings.ollama_model
        self.base = base_url or settings.ollama_url.rstrip("/")

    def _embed(self, text: str) -> list[float]:
        url = f"{self.base}/api/embed"
        payload = {"model": self.model, "input": text}
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Ollama /api/embed returns {"model":"...", "embeddings":[[...]]} for single input
        embeddings = data.get("embeddings")
        if isinstance(embeddings, list) and len(embeddings) > 0:
            first = embeddings[0]
            if isinstance(first, list):
                return normalize(list(map(float, first)))
            return normalize(list(map(float, embeddings)))
        # Fallback for older /api/embeddings format: {"embedding": [...]}
        emb = data.get("embedding")
        if isinstance(emb, list):
            return normalize(list(map(float, emb)))
        raise ValueError("Unexpected embed response from ollama")

    def embed_text(self, text: str) -> list[float]:
        try:
            return self._embed(text)
        except Exception:
            # fallback to deterministic local embed
            return AIService().embed_text(text)

    def analyze_review(self, review_text: str, rating: int) -> ReviewAnalysis:
        # Get embedding first
        embedding = self.embed_text(review_text)
        # Use prompt to ask model to extract liked/disliked/sentiment in JSON
        prompt = (
            "Extract liked_features (list), disliked_features (list), and sentiment (positive/neutral/negative)"
            f" from the following user review and return a JSON object:\n\n{review_text}\n\nRating: {rating}\n\nRespond with only JSON."
        )
        try:
            url = f"{self.base}/api/generate"
            payload = {"model": self.model, "input": prompt}
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            out = resp.json()
            text = ""
            if isinstance(out, dict):
                # Ollama may return {'id':..., 'model':..., 'object':..., 'data': [{'content': '...'}]}
                if "data" in out and isinstance(out["data"], list):
                    text = "".join(item.get("content", "") for item in out["data"]) or out.get("content", "")
                else:
                    text = out.get("content", "") or json.dumps(out)
            else:
                text = str(out)

            # attempt to parse JSON from model output
            parsed = None
            try:
                parsed = json.loads(text)
            except Exception:
                # try to find JSON substring
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    parsed = json.loads(text[start:end+1])

            if parsed and isinstance(parsed, dict):
                liked = parsed.get("liked_features") or parsed.get("liked") or []
                disliked = parsed.get("disliked_features") or parsed.get("disliked") or []
                sentiment = parsed.get("sentiment") or parsed.get("tone") or "neutral"
                return ReviewAnalysis(liked_features=list(liked), disliked_features=list(disliked), sentiment=str(sentiment), embedding=embedding)
        except Exception:
            pass

        # fallback to deterministic local analyzer
        return AIService().analyze_review(review_text, rating)

    def explain_recommendation(self, game: Any, score: float, group_features: list[str] | None = None) -> str:
        prompt = (
            f"Write a concise explanation why the game '{game.title}' (tags: {', '.join(game.tags or [])}) is a good fit for a group's preferences."
            f" Include the similarity as a percentage: {round(score*100)}%"
        )
        try:
            url = f"{self.base}/api/generate"
            payload = {"model": self.model, "input": prompt}
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            out = resp.json()
            if isinstance(out, dict) and "data" in out:
                return "".join(item.get("content", "") for item in out["data"]) or str(out)
            return str(out)
        except Exception:
            return AIService().explain_recommendation(game, score, group_features)


_cached_provider: BaseLLMProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    global _cached_provider
    if _cached_provider is not None:
        return _cached_provider
    if settings.ai_provider == "ollama":
        # attempt to autodiscover a good model if one isn't configured
        model = settings.ollama_model
        if not model:
            try:
                model = _discover_ollama_model(settings.ollama_url)
                if model:
                    logging.getLogger("llm_provider").info("auto-selected ollama model: %s", model)
            except Exception:
                # discovery failed; provider will still be created and will fallback on use
                model = None
        _cached_provider = OllamaProvider(model=model)
    else:
        _cached_provider = AIService()
    return _cached_provider


def _discover_ollama_model(base_url: str | None) -> str | None:
    """Query the Ollama server for installed models and pick a best candidate.

    Returns a model name or None if discovery failed or no models found.
    The heuristic prefers models whose names contain common LLM identifiers.
    """
    if not base_url:
        return None
    base = base_url.rstrip("/")
    try:
        url = f"{base}/api/models"
        resp = requests.get(url, timeout=4)
        resp.raise_for_status()
        data = resp.json()
        # data may be a list or a dict containing 'models'
        models = []
        if isinstance(data, dict) and "models" in data and isinstance(data["models"], list):
            models = data["models"]
        elif isinstance(data, list):
            models = data

        names: list[str] = []
        for item in models:
            if isinstance(item, dict):
                name = item.get("name") or item.get("id") or item.get("model")
            else:
                name = str(item)
            if name:
                names.append(name)

        if not names:
            return None

        # prefer explicit embedding-capable or large LLM-like names
        priority = ["embedding", "embed", "gpt", "llama", "llama2", "mistral", "mixtral", "vicuna", "gpt4o", "gpt-4"]
        lowered = [n.lower() for n in names]
        for p in priority:
            for i, n in enumerate(lowered):
                if p in n:
                    return names[i]

        # fallback: return the first available model name
        return names[0]
    except Exception:
        return None
