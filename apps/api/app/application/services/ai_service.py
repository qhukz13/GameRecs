from app.application.services.vector_math import normalize
from app.core.config import settings
from app.domain.entities import ReviewAnalysis
from app.infrastructure.db.models import GameModel


class AIService:
    vocabulary = (
        "strategy",
        "combat",
        "story",
        "puzzle",
        "survival",
        "building",
        "casual",
        "chaos",
    )

    positive_words = {
        "love",
        "liked",
        "great",
        "fun",
        "excellent",
        "best",
        "enjoyed",
        "люблю",
        "понрав",
        "класс",
        "весело",
        "отлич",
    }
    negative_words = {
        "hate",
        "boring",
        "bad",
        "slow",
        "annoying",
        "frustrating",
        "disliked",
        "скуч",
        "плох",
        "раздраж",
        "медлен",
    }

    def embed_text(self, text: str) -> list[float]:
        lower = text.lower()
        vector: list[float] = []
        for term in self.vocabulary[: settings.embedding_dim]:
            direct = lower.count(term)
            fuzzy = sum(1 for word in lower.split() if term[:4] in word)
            vector.append(float(direct * 2 + fuzzy))
        if not any(vector):
            for index, char in enumerate(lower.encode("utf-8")):
                vector[index % settings.embedding_dim] += (char % 17) / 17
        return normalize(vector)

    def embed_game(self, title: str, description: str, genres: list[str], tags: list[str]) -> list[float]:
        return self.embed_text(" ".join([title, description, *genres, *tags]))

    def analyze_review(self, review_text: str, rating: int) -> ReviewAnalysis:
        lower = review_text.lower()
        liked = [term for term in self.vocabulary if term in lower]
        disliked = [term for term in self.vocabulary if f"not {term}" in lower or f"no {term}" in lower]

        positive_hits = sum(1 for word in self.positive_words if word in lower)
        negative_hits = sum(1 for word in self.negative_words if word in lower)
        if rating >= 8 or positive_hits > negative_hits:
            sentiment = "positive"
        elif rating <= 4 or negative_hits > positive_hits:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        if sentiment == "positive" and not liked:
            liked = ["cooperative flow"]
        if sentiment == "negative" and not disliked:
            disliked = ["friction"]

        return ReviewAnalysis(
            liked_features=liked,
            disliked_features=disliked,
            sentiment=sentiment,
            embedding=self.embed_text(review_text),
        )

    def explain_recommendation(
        self, game: GameModel, score: float, group_features: list[str] | None = None
    ) -> str:
        features = ", ".join(group_features or game.tags[:3] or game.genres[:3] or ["co-op play"])
        percent = round(score * 100)
        return f"{game.title} matches the group's preference profile around {features}; similarity score {percent}%."

