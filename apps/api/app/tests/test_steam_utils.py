"""Tests for steam_utils helper functions."""

from app.application.services.steam_utils import (
    BLACKLIST_CATEGORIES,
    GAME_KEYWORDS,
    has_blacklist_categories,
    is_game_like,
)


def test_has_blacklist_categories_true() -> None:
    assert has_blacklist_categories(["Action", "DLC"], ["Co-op"]) is True
    assert has_blacklist_categories(["Soundtrack"], []) is True
    assert has_blacklist_categories([], ["tool", "Utility"]) is True
    assert has_blacklist_categories(["Demo"], []) is True
    assert has_blacklist_categories([], ["downloadable content"]) is True


def test_has_blacklist_categories_false() -> None:
    assert has_blacklist_categories(["Action", "Adventure"], ["Co-op"]) is False
    assert has_blacklist_categories([], []) is False
    assert has_blacklist_categories(None, ["RPG"]) is False
    assert has_blacklist_categories(["Strategy"], None) is False


def test_is_game_like_true() -> None:
    assert is_game_like(["Action", "Adventure"], ["Co-op"]) is True
    assert is_game_like(["RPG", "Strategy"], ["Single-player"]) is True
    assert is_game_like(["Indie"], ["Multiplayer", "FPS"]) is True
    assert is_game_like(["Casual"], ["Free to Play"]) is True


def test_is_game_like_false() -> None:
    assert is_game_like(["Software"], ["Utility"]) is False
    assert is_game_like([], []) is False
    assert is_game_like(None, None) is False


def test_constants_are_non_empty() -> None:
    assert len(BLACKLIST_CATEGORIES) > 0
    assert len(GAME_KEYWORDS) > 0
    assert "dlc" in BLACKLIST_CATEGORIES
    assert "co-op" in GAME_KEYWORDS