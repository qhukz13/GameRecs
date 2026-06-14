"""Shared utilities for Steam API integration used by RecommendationService."""

import logging
from typing import Any

BLACKLIST_CATEGORIES: list[str] = [
    "downloadable content",
    "dlc",
    "soundtrack",
    "tool",
    "software",
    "utility",
    "demo",
]

GAME_KEYWORDS: list[str] = [
    "action",
    "adventure",
    "rpg",
    "role-playing",
    "simulation",
    "strategy",
    "puzzle",
    "racing",
    "sports",
    "shooter",
    "fps",
    "roguelike",
    "indie",
    "casual",
    "arcade",
    "platformer",
    "visual novel",
    "co-op",
    "cooperative",
    "multiplayer",
    "single-player",
    "free to play",
]


def has_blacklist_categories(genres: list[str] | None, tags: list[str] | None) -> bool:
    """Check if genres/tags contain any blacklisted non-game categories (DLC, soundtrack, etc.)."""
    for s in list(genres or []) + list(tags or []):
        if not s:
            continue
        sl = s.lower()
        for bk in BLACKLIST_CATEGORIES:
            if bk in sl:
                return True
    return False


def is_game_like(genres: list[str] | None, tags: list[str] | None) -> bool:
    """Heuristic check if genres/tags suggest this is a game (not a tool, etc.)."""
    for s in list(genres or []) + list(tags or []):
        if not s:
            continue
        sl = s.lower()
        for kw in GAME_KEYWORDS:
            if kw in sl:
                return True
    return False


def log_skipped_steam_item(sid: str, genres: list[str], tags: list[str]) -> None:
    """Log a skipped Steam item with its categories."""
    logging.getLogger(__name__).info(
        "Skipping steam:%s due to blacklist categories: %s %s", sid, genres, tags
    )