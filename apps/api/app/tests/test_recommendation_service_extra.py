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
        self._candidates = candidates

    def search_similar(self, embedding, exclude_game_ids, limit):
        # filter out excluded IDs to simulate repo behavior
        filtered = [c for c in self._candidates if c[0].id not in (exclude_game_ids or set())]
        return filtered[:limit]


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
        self.embedding = embedding

    def update_group_profile(self, group_id: UUID):
        return self.embedding


class _AIStub:
    def explain_recommendation(self, game, score, group_features=None):
        return f"{game.title} explained ({int(score*100)}%)"


def test_generate_returns_empty_when_group_profile_missing() -> None:
    group_id = uuid4()

    g1 = _DummyGame(uuid4(), "Alpha Co-op", tags=["co-op"], release_date=datetime(2021, 6, 15, tzinfo=timezone.utc))

    games = _GamesRepoStub([(g1, 0.9)])
    reviews = _ReviewsRepoStub()
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub(embedding=None)  # group profile missing
    ai = _AIStub()

    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    saved = service.generate_for_group(group_id)

    assert saved == []
    assert recs.saved == []


def test_generate_excludes_played_games() -> None:
    group_id = uuid4()

    g1 = _DummyGame(uuid4(), "Alpha Co-op", tags=["co-op"], release_date=datetime(2021, 6, 15, tzinfo=timezone.utc))
    g2 = _DummyGame(uuid4(), "Puzzle Night", tags=["co-op"], release_date=datetime(2022, 1, 1, tzinfo=timezone.utc))

    candidates = [(g1, 0.9), (g2, 0.6)]
    games = _GamesRepoStub(candidates)
    # mark g1 as already played by the group
    reviews = _ReviewsRepoStub(played_ids=[g1.id])
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub(embedding=[1.0] * 8)
    ai = _AIStub()

    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    saved = service.generate_for_group(group_id, limit=5)

    # only g2 should be recommended because g1 is excluded
    assert len(saved) == 1
    assert recs.saved[0].game_id == g2.id


def test_generate_candidates_fallback_when_group_profile_missing() -> None:
    group_id = uuid4()
    
    g1 = _DummyGame(uuid4(), "Alpha Co-op", tags=["co-op"], release_date=datetime(2021, 6, 15, tzinfo=timezone.utc))
    games = _GamesRepoStub([(g1, 0.9)])
    reviews = _ReviewsRepoStub()
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub(embedding=None)  # missing group profile
    ai = _AIStub()
    
    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    candidates = service.generate_candidates_for_group(group_id, limit=5)
    
    # generate_candidates_for_group should succeed using a neutral embedding and return candidates
    assert len(candidates) == 1
    assert candidates[0]["game_id"] == str(g1.id)
    assert candidates[0]["explanation"] == "Popular co-op recommendation."

