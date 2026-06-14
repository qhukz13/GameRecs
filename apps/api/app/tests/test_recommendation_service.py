from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.services.recommendation_service import RecommendationService


class _DummyGame:
    def __init__(self, id: UUID, title: str, tags=None, genres=None, release_date=None, description=""):
        self.id = id
        self.title = title
        self.tags = tags or []
        self.genres = genres or []
        self.release_date = release_date
        self.description = description


class _GamesRepoStub:
    def __init__(self, candidates):
        # candidates: list[tuple[Game, float]]
        self._candidates = candidates

    def search_similar(self, embedding, exclude_game_ids, limit):
        # ignore embedding/exclude/limit in stub; return preset
        return self._candidates[:limit]


class _ReviewsRepoStub:
    def __init__(self, played_ids=None):
        self._played = set(played_ids or [])

    def played_game_ids_for_group(self, group_id: UUID):
        return self._played


class _RecommendationsRepoStub:
    def __init__(self):
        self.saved = []

    def upsert(self, group_id: UUID, game_id: UUID, score: float, explanation: str):
        obj = type("R", (), {"group_id": group_id, "game_id": game_id, "score": score, "explanation": explanation})
        self.saved.append(obj)
        return obj


class _ProfileServiceStub:
    def __init__(self, embedding=None):
        self.embedding = embedding or [1.0] * 8

    def update_group_profile(self, group_id: UUID):
        return self.embedding


class _AIStub:
    def explain_recommendation(self, game, score, group_features=None):
        return f"{game.title} explained ({int(score*100)}%)"


def test_generate_for_group_creates_and_saves_recommendations() -> None:
    group_id = uuid4()

    # prepare two candidate games with co-op tags and release_date >= 2020 to pass filters
    g1 = _DummyGame(uuid4(), "Alpha Co-op", tags=["co-op", "combat"], release_date=datetime(2021, 6, 15, tzinfo=timezone.utc)) 
    g2 = _DummyGame(uuid4(), "Puzzle Night", tags=["co-op", "puzzle"], release_date=datetime(2022, 1, 1, tzinfo=timezone.utc)) 
    candidates = [(g1, 0.92), (g2, 0.61)]

    games = _GamesRepoStub(candidates)
    reviews = _ReviewsRepoStub(played_ids=[])  # nothing played
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub()
    ai = _AIStub()

    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    saved = service.generate_for_group(group_id, limit=5)

    assert len(saved) == 2
    assert recs.saved and len(recs.saved) == 2
    assert recs.saved[0].game_id == g1.id
    assert recs.saved[1].game_id == g2.id
    assert "explained" in recs.saved[0].explanation


def test_generate_filters_out_games_without_release_date() -> None:
    """Games with no release_date should be filtered out because _is_new_game returns False."""
    group_id = uuid4()

    g1 = _DummyGame(uuid4(), "Old Game", tags=["co-op"], release_date=datetime(2018, 1, 1, tzinfo=timezone.utc))
    g2 = _DummyGame(uuid4(), "No Date Game", tags=["co-op"], release_date=None)
    g3 = _DummyGame(uuid4(), "New Game", tags=["co-op"], release_date=datetime(2022, 6, 1, tzinfo=timezone.utc))

    candidates = [(g1, 0.9), (g2, 0.85), (g3, 0.8)]
    games = _GamesRepoStub(candidates)
    reviews = _ReviewsRepoStub()
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub()
    ai = _AIStub()

    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    saved = service.generate_for_group(group_id, limit=5)

    # Only g3 (new, 2022) should pass the co-op + new game filter
    assert len(saved) == 1
    assert recs.saved[0].game_id == g3.id
