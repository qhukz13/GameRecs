"""Shared utilities for Steam API integration used by RecommendationService."""

import logging
from datetime import datetime
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

# Import _parse_steam_release_date from recommendation_service
from app.application.services.steam_parsing import _parse_steam_release_date


def is_game_like(genres: list[str] | None, tags: list[str] | None, release_date: datetime | None = None) -> bool:
    """Heuristic check if genres/tags suggest this is a game (not a tool, etc.)."""
    for s in list(genres or []) + list(tags or []):
        if not s:
            continue
        sl = s.lower()
        for kw in GAME_KEYWORDS:
            if kw in sl:
                return True
    return False


def _is_coop_game(genres: list[str] | None, tags: list[str] | None, description: str | None = None, data: dict | None = None) -> bool:
    """
    Strict check: game MUST have cooperative keywords in genres, tags, or description.
    Only games that are explicitly co-op and new qualify — no false positives for PvP/single-player-only games.
    """
    # Strict co-op keywords — must contain one of these exact substrings in genres/tags/description
    coop_keywords = [
        "co-op", "cooperative", "coop", "co-op campaign",
        "online co-op", "local co-op", "co-op multiplayer",
        "pve co-op", "co-op pve", "co-op survival",
        "cooperative play", "cooperative gameplay",
        "co-op mode", "co-op action", "co-op adventure",
        "co-op shooter", "co-op strategy",
    ]
    all_terms = [t.lower() for t in (genres or []) + (tags or [])]
    if description:
        all_terms.append(description.lower())

    for term in all_terms:
        for kw in coop_keywords:
            if kw in term:
                return True

# Ensure proper logging for skipped items
    has_multiplayer = any("multiplayer" in t.lower() for t in (tags or []))
    if has_multiplayer and description:
        desc_lower = description.lower()
        for kw in coop_keywords:
            if kw in desc_lower:
                return True

    return False

def log_skipped_steam_item(sid: str, genres: list[str], tags: list[str], release_date: datetime | None = None) -> None:
    """Log a skipped Steam item with its categories."""
    logging.getLogger(__name__).info(
        "Skipping steam:%s due to blacklist categories: %s %s, release_date: %s", sid, genres, tags, release_date if release_date else "None"
    )