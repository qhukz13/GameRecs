"""Tests for Steam API integration with mocked requests."""

from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.application.services.recommendation_service import (
    RecommendationService,
    _parse_steam_release_date,
    _is_new_game,
)


class _DummyGame:
    def __init__(self, id, title, tags=None, genres=None, release_date=None):
        self.id = id
        self.title = title
        self.tags = tags or []
        self.genres = genres or []
        self.release_date = release_date


class _GamesRepoStub:
    def __init__(self, candidates=None):
        self._candidates = candidates or []
        self.created = []

    def search_similar(self, embedding, exclude_game_ids, limit):
        return self._candidates[:limit]

    def create(self, **kwargs):
        game = _DummyGame(
            id=uuid4(),
            title=kwargs.get("title", ""),
            tags=kwargs.get("tags", []),
            genres=kwargs.get("genres", []),
            release_date=kwargs.get("release_date"),
        )
        self.created.append(game)
        return game


class _ReviewsRepoStub:
    def __init__(self, played_ids=None):
        self._played = set(played_ids or [])

    def played_game_ids_for_group(self, group_id):
        return self._played


class _RecommendationsRepoStub:
    def __init__(self):
        self.saved = []

    def upsert(self, group_id, game_id, score, explanation):
        obj = type("R", (), {"group_id": group_id, "game_id": game_id, "score": score, "explanation": explanation})
        self.saved.append(obj)
        return obj


class _ProfileServiceStub:
    def __init__(self, embedding=None):
        self.embedding = embedding or [1.0] * 8

    def update_group_profile(self, group_id):
        return self.embedding


class _AIStub:
    def explain_recommendation(self, game, score, group_features=None):
        return f"{game.title} explained ({int(score*100)}%)"

    def embed_text(self, text):
        return [0.1] * 8


def make_mock_storesearch_response(items: list[dict]) -> MagicMock:
    """Create a mock requests.Response for Steam store/search."""
    mock = MagicMock()
    mock.json.return_value = {"items": items}
    mock.raise_for_status.return_value = None
    return mock


def make_mock_appdetails_response(app_id: str, data: dict | None) -> MagicMock:
    """Create a mock requests.Response for Steam API appdetails."""
    mock = MagicMock()
    mock.json.return_value = {app_id: {"success": data is not None, "data": data}}
    mock.raise_for_status.return_value = None
    return mock


@patch("app.application.services.recommendation_service.requests.get")
def test_generate_falls_back_to_local_when_steam_fails(mock_get) -> None:
    """When Steam API is unreachable, fall back to local DB search."""
    mock_get.side_effect = Exception("Connection refused")

    group_id = uuid4()
    g1 = _DummyGame(uuid4(), "Local Co-op", tags=["co-op"], release_date=datetime(2022, 1, 1, tzinfo=timezone.utc))

    games = _GamesRepoStub(candidates=[(g1, 0.9)])
    reviews = _ReviewsRepoStub()
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub()
    ai = _AIStub()

    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    saved = service.generate_for_group(group_id, limit=5)

    # Should still get local candidates via fallback
    assert len(saved) == 1
    assert recs.saved[0].game_id == g1.id


@patch("app.application.services.recommendation_service.requests.get")
def test_generate_skips_non_game_steam_entries(mock_get) -> None:
    """Steam entries with non-game types should be skipped."""
    group_id = uuid4()
    game_id = uuid4()

    # First call -> store/search returns a candidate app id
    # Second call -> appdetails returns a non-game (type='application')
    mock_get.side_effect = [
        make_mock_storesearch_response([{"id": "12345", "name": "Test Tool"}]),
        make_mock_appdetails_response("12345", {
            "type": "application",
            "name": "Some Tool",
            "short_description": "A tool",
            "genres": [{"description": "Software"}],
            "categories": [{"description": "Utility"}],
            "release_date": {"date": "2022-01-01"},
        }),
    ]

    # Provide a local candidate for fallback
    g1 = _DummyGame(game_id, "Real Game", tags=["co-op"], release_date=datetime(2022, 1, 1, tzinfo=timezone.utc))
    games = _GamesRepoStub(candidates=[(g1, 0.9)])
    reviews = _ReviewsRepoStub()
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub()
    ai = _AIStub()

    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    saved = service.generate_for_group(group_id, limit=5)

    # Should get local candidate because Steam returned non-game
    assert len(saved) == 1
    assert recs.saved[0].game_id == game_id


@patch("app.application.services.recommendation_service.requests.get")
def test_generate_skips_blacklisted_steam_categories(mock_get) -> None:
    """Steam entries with DLC/soundtrack categories should be skipped."""
    group_id = uuid4()
    game_id = uuid4()

    mock_get.side_effect = [
        make_mock_storesearch_response([{"id": "999", "name": "Some DLC"}]),
        make_mock_appdetails_response("999", {
            "type": "game",
            "name": "Premium DLC Pack",
            "short_description": "Extra content",
            "genres": [{"description": "Action"}],
            "categories": [{"description": "Downloadable Content"}, {"description": "Co-op"}],
            "release_date": {"date": "2022-01-01"},
        }),
    ]

    g1 = _DummyGame(game_id, "Real Game", tags=["co-op"], release_date=datetime(2022, 1, 1, tzinfo=timezone.utc))
    games = _GamesRepoStub(candidates=[(g1, 0.9)])
    reviews = _ReviewsRepoStub()
    recs = _RecommendationsRepoStub()
    profiles = _ProfileServiceStub()
    ai = _AIStub()

    service = RecommendationService(games=games, reviews=reviews, recommendations=recs, profiles=profiles, ai=ai)
    saved = service.generate_for_group(group_id, limit=5)

    # Should get local candidate because Steam returned DLC
    assert len(saved) == 1
    assert recs.saved[0].game_id == game_id


def test_parse_steam_release_date() -> None:
    """Test _parse_steam_release_date with various formats."""
    assert _parse_steam_release_date({"date": "Oct 21, 2022", "coming_soon": False}) is not None
    assert _parse_steam_release_date({"date": "2022-10-21", "coming_soon": False}) is not None
    assert _parse_steam_release_date({"date": "Oct 21, 2022", "coming_soon": True}) is None
    assert _parse_steam_release_date({}) is None
    assert _parse_steam_release_date(None) is None


def test_is_new_game() -> None:
    """Test _is_new_game helper."""
    assert _is_new_game(datetime(2022, 6, 1, tzinfo=timezone.utc)) is True
    assert _is_new_game(datetime(2020, 1, 1, tzinfo=timezone.utc)) is True
    assert _is_new_game(datetime(2019, 12, 31, tzinfo=timezone.utc)) is False
    assert _is_new_game(None) is False