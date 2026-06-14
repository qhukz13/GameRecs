import types

from app.application.services.llm_provider import OllamaProvider
from app.core.config import settings


class _MockResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_analyze_review_parses_json_direct(monkeypatch):
    base = "http://ollama.test"
    model = "test-model"

    def fake_post(url, json=None, timeout=None):
        if url.endswith("/api/embed"):
            # return a straightforward embedding list
            return _MockResp({"embedding": [0.1] * settings.embedding_dim})
        if url.endswith("/api/generate"):
            # model returns JSON inside data.content
            content = '{"liked_features": ["coop","puzzle"], "disliked_features": [], "sentiment": "positive"}'
            return _MockResp({"data": [{"content": content}]})
        return _MockResp({})

    monkeypatch.setattr("requests.post", fake_post)

    prov = OllamaProvider(model=model, base_url=base)
    analysis = prov.analyze_review("Great co-op puzzles", 5)
    assert "coop" in analysis.liked_features
    assert analysis.disliked_features == []
    assert analysis.sentiment.lower().startswith("positive")
    assert isinstance(analysis.embedding, list)
    assert len(analysis.embedding) == settings.embedding_dim


def test_analyze_review_parses_embedded_json(monkeypatch):
    base = "http://ollama.test"
    model = "test-model"

    def fake_post(url, json=None, timeout=None):
        if url.endswith("/api/embed"):
            return _MockResp({"embedding": [0.2] * settings.embedding_dim})
        if url.endswith("/api/generate"):
            # model returns a leading explanation then JSON
            content = 'Here is the analysis:\n{"liked_features": ["story"], "disliked_features": ["bugs"], "sentiment": "neutral"}'
            return _MockResp({"data": [{"content": content}]})
        return _MockResp({})

    monkeypatch.setattr("requests.post", fake_post)

    prov = OllamaProvider(model=model, base_url=base)
    analysis = prov.analyze_review("Mixed feelings", 3)
    assert "story" in analysis.liked_features
    assert "bugs" in analysis.disliked_features
    assert analysis.sentiment.lower().startswith("neutral")


def test_explain_recommendation_extracts_text(monkeypatch):
    base = "http://ollama.test"
    model = "test-model"

    def fake_post(url, json=None, timeout=None):
        if url.endswith("/api/generate"):
            return _MockResp({"data": [{"content": "This game fits because of cooperative puzzles and story."}]})
        if url.endswith("/api/embed"):
            return _MockResp({"embedding": [0.3] * settings.embedding_dim})
        return _MockResp({})

    monkeypatch.setattr("requests.post", fake_post)

    prov = OllamaProvider(model=model, base_url=base)
    game = types.SimpleNamespace(title="It Takes Two", tags=["puzzle", "coop"]) 
    explanation = prov.explain_recommendation(game, 0.42, group_features=["story", "puzzle"])
    assert isinstance(explanation, str)
    assert "cooperative" in explanation or "cooperative" in explanation.lower() or "cooperative" in explanation
