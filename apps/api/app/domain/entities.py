from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewAnalysis:
    liked_features: list[str]
    disliked_features: list[str]
    sentiment: str
    embedding: list[float]


@dataclass(frozen=True)
class SimilarGame:
    game_id: str
    score: float

