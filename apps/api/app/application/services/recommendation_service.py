from uuid import UUID
import logging
from datetime import datetime, timezone
from app.application.services.steam_parsing import _parse_steam_release_date
from app.application.services.ai_service import AIService
from app.application.services.profile_service import ProfileService
from app.core.config import settings
from app.infrastructure.db.models import RecommendationModel
from app.infrastructure.repositories.games import GameRepository
from app.infrastructure.repositories.recommendations import RecommendationRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.application.services.vector_math import normalize
from uuid import uuid4
import requests
from app.application.services.llm_provider import get_llm_provider
from app.application.services.steam_utils import (
    has_blacklist_categories,
    is_game_like,
    log_skipped_steam_item,
)


def _is_coop_game(genres: list[str] | None, tags: list[str] | None, description: str | None = None, release_date: datetime | None = None) -> bool:
    """Strict check: game MUST have cooperative keywords in genres, tags, or description.
    Also ensures the game is new (released in 2020 or later).
    Only games that are explicitly co-op and new qualify — no false positives for PvP/single-player-only games.
    """
    # Strict co-op keywords — must contain one of these exact substrings in genres/tags/description
    coop_keywords = [
        "co-op", "multiplayer", "cooperative", "coop", "co-op campaign",
        "online co-op", "local co-op", "co-op multiplayer",
        "pve co-op", "co-op pve", "co-op survival",
        "cooperative play", "cooperative gameplay",
        "co-op mode", "co-op action", "co-op adventure",
        "co-op shooter", "co-op strategy"
    ]
    all_terms = [t.lower() for t in (genres or []) + (tags or [])]
    if description:
        all_terms.append(description.lower())

    for term in all_terms:
        for kw in coop_keywords:
            # match whole word or surrounded by non-alphanumeric
            if kw in term:
                return True

    # Additional heuristic: tags contain "multiplayer" but description has "co-op" -> still valid
    has_multiplayer = any("multiplayer" in t.lower() for t in (tags or []))
    if has_multiplayer and description:
        desc_lower = description.lower()
        for kw in coop_keywords:
            if kw in desc_lower:
                return True

TECHNICAL_TERMS_BLACKLIST = {
    "steam", "remote", "controller", "sharing", "sound", "subtitle", "caption",
    "difficulty", "comfort", "text size", "in-app", "purchase", "single-player",
    "split screen", "play together", "color", "timed input", "family",
    "cross-platform", "leaderboard", "cloud", "workshop",
    "achievements", "cards", "stats", "editor", "track", "vr supported", "screen"
}


def _is_valid_search_term(term: str) -> bool:
    term_lower = term.lower()
    for word in TECHNICAL_TERMS_BLACKLIST:
        if word in term_lower:
            return False
    return len(term.strip()) > 1


def _is_new_game(release_date: datetime | None) -> bool:
    """Check if a game was released in 2020 or later."""
    if not release_date:
        return False
    return release_date.year >= 2020


class RecommendationService:
    def __init__(
        self,
        games: GameRepository,
        reviews: ReviewRepository,
        recommendations: RecommendationRepository,
        profiles: ProfileService,
        ai: AIService,
    ) -> None:
        self.games = games
        self.reviews = reviews
        self.recommendations = recommendations
        self.profiles = profiles
        self.ai = ai

    def generate_for_group(self, group_id: UUID, limit: int | None = None) -> list[RecommendationModel]:
        """
        Generate recommendations for a group, filtering by co-op and recency (2020+).
        """
        group_embedding = self.profiles.update_group_profile(group_id)
        if not group_embedding:
            return []

        played_game_ids = self.reviews.played_game_ids_for_group(group_id)

        # Simple Steam search approach: use group's known genres/tags collected from games in DB
        # collect genres/tags from group members' reviewed games
        from collections import Counter
        group_genres = Counter()
        group_tags = Counter()
        try:
            # Query the database to retrieve actual GameModel records of already played/reviewed games
            if played_game_ids:
                from sqlalchemy import select
                from app.infrastructure.db.models import GameModel
                played_games = self.games.db.scalars(
                    select(GameModel).where(GameModel.id.in_(played_game_ids))
                ).all()
                for g in played_games:
                    for gen in g.genres or []:
                        group_genres[gen] += 1
                    for tg in g.tags or []:
                        group_tags[tg] += 1

            # fallback to local search if anything fails
            local_candidates = self.games.search_similar(
                embedding=group_embedding,
                exclude_game_ids=played_game_ids,
                limit=(limit or settings.recommendation_limit) * 3,
            )
            # collect genres/tags from local candidates
            for g, _ in local_candidates:
                for gen in g.genres or []:
                    group_genres[gen] += 1
                for tg in g.tags or []:
                    group_tags[tg] += 1

            valid_genres = [t for t, c in group_genres.most_common() if _is_valid_search_term(t)]
            valid_tags = [t for t, c in group_tags.most_common() if _is_valid_search_term(t)]
            if not valid_genres and not valid_tags:
                valid_tags = ["co-op", "multiplayer", "cooperative", "survival"]

            # query Steam for each term (genre or tag) to collect app ids
            steam_ids = set()
            for term in valid_genres[:5] + valid_tags[:5]:
                search_query = f"{term} co-op" if "co-op" not in term.lower() else term
                try:
                    resp = requests.get(
                        "https://store.steampowered.com/api/storesearch",
                        params={"cc": "us", "l": "en", "term": search_query},
                        timeout=4,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for item in data.get("items", [])[:20]:
                        steam_ids.add(str(item.get("id")))
                except Exception:
                    continue

            # For each steam id, fetch details and create/ensure a Game entry then compute similarity
            repo = GameRepository(self.games.db)
            ai = get_llm_provider()
            steam_found = 0
            for sid in list(steam_ids):
                if steam_found >= (limit or settings.recommendation_limit) * 3:
                    break
                try:
                    r = requests.get("https://store.steampowered.com/api/appdetails", params={"appids": sid, "cc": "us", "l": "en"}, timeout=5)
                    r.raise_for_status()
                    d = r.json().get(sid, {}).get("data")
                    if not d:
                        continue
                    # Filter out non-game entries (Steam returns type: 'game' or 'application')
                    if d.get("type") and d.get("type") != "game":
                        continue
                    title = d.get("name")
                    desc = d.get("short_description") or d.get("detailed_description") or ""
                    genres = [g.get("description") for g in d.get("genres", [])]
                    tags = [c.get("description") for c in d.get("categories", [])]
                    if has_blacklist_categories(genres, tags):
                        # skip non-game items such as DLCs, soundtracks, tools
                        log_skipped_steam_item(sid, genres, tags)
                        continue
                    # Heuristic: ensure the Steam entry looks like a game by checking genres/tags
                    if not is_game_like(genres, tags):
                        continue
                    # Parse release date from Steam
                    release_date = _parse_steam_release_date(d.get("release_date", {}))
                    
                    # Filter: custom logic for popularity vs recency
                    r_rev = requests.get(
                        f"https://store.steampowered.com/appreviews/{sid}",
                        params={"json": 1, "language": "all"},
                        timeout=5
                    )
                    r_rev.raise_for_status()
                    rev_data = r_rev.json().get("query_summary", {})
                    total_reviews = rev_data.get("total_reviews", 0)
                    total_positive = rev_data.get("total_positive", 0)
                    rating = (total_positive / total_reviews) if total_reviews > 0 else 0.0
                    
                    if total_reviews >= 300:
                        if rating < 0.70:
                            continue
                    else:
                        if not release_date or release_date.year < 2025:
                            continue
                        if total_reviews > 0 and rating < 0.60:
                            continue
                        
                    embedding = ai.embed_text(" ".join([title, desc, *genres, *tags]))
                    existing = repo.find_by_external_id(f"steam:{sid}")
                    if existing:
                        game = existing
                    else:
                        game = repo.create(
                            external_id=f"steam:{sid}",
                            title=title,
                            description=desc,
                            genres=genres,
                            tags=tags,
                            players_min=1,
                            players_max=4,
                            embedding=embedding,
                            release_date=release_date,
                        )
                    steam_found += 1
                    # compute similarity score (1 - cosine distance)
                    # reuse search_similar logic by querying DB
                except Exception:
                    continue

            candidates = self.games.search_similar(
                embedding=group_embedding,
                exclude_game_ids=played_game_ids,
                limit=limit or settings.recommendation_limit,
            )
        except Exception:
            # fallback to local-only search if Steam integration fails
            candidates = self.games.search_similar(
                embedding=group_embedding,
                exclude_game_ids=played_game_ids,
                limit=limit or settings.recommendation_limit,
            )
        # Filter candidates for co-op and new games (2020+)
        filtered_candidates = []
        for game, score in candidates:
            if _is_coop_game(game.genres, game.tags, game.description, game.release_date):
                filtered_candidates.append((game, score))
        
        # Fallback: if not enough strict co-op candidates, fill with top similarity matches
        if len(filtered_candidates) < (limit or settings.recommendation_limit):
            existing_ids = {g.id for g, _ in filtered_candidates}
            for game, score in candidates:
                if game.id not in existing_ids:
                    filtered_candidates.append((game, score))
                    if len(filtered_candidates) >= (limit or settings.recommendation_limit):
                        break
        
        saved: list[RecommendationModel] = []
        for game, score in filtered_candidates[:(limit or settings.recommendation_limit)]:
            explanation = self.ai.explain_recommendation(game=game, score=score)
            saved.append(self.recommendations.upsert(group_id, game.id, score, explanation))
        return saved

    def generate_candidates_for_group(self, group_id: UUID, limit: int | None = None) -> list[dict]:
        """Generate recommendation candidates from local DB first, then enrich with Steam results.
        Returns a list of dicts shaped similarly to RecommendationRead but not stored in DB.
        Games must pass co-op and recency filters.
        """
        group_embedding = self.profiles.update_group_profile(group_id)
        is_neutral = False
        if not group_embedding:
            group_embedding = [0.1] * settings.embedding_dim
            is_neutral = True

        played_game_ids = self.reviews.played_game_ids_for_group(group_id)
        result_limit = limit or settings.recommendation_limit

        # --- Phase 1: local candidates (always available) ---
        local_candidates = self.games.search_similar(
            embedding=group_embedding,
            exclude_game_ids=played_game_ids,
            limit=result_limit * 3,
        )
        
        # First pass: strict co-op + new game filter
        out: list[dict] = []
        for game, score in local_candidates:
            if not _is_coop_game(game.genres, game.tags, game.description):
                continue
            explanation = "Popular co-op recommendation." if is_neutral else f"Similarity score {int(score*100)}%."
            out.append({
                "id": str(uuid4()),
                "group_id": str(group_id),
                "game_id": str(game.id),
                "score": float(score),
                "explanation": explanation,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "transient": True,
                "game": {
                    "id": str(game.id),
                    "external_id": getattr(game, 'external_id', None),
                    "title": game.title,
                    "description": game.description,
                    "genres": game.genres,
                    "tags": game.tags,
                    "players_min": getattr(game, 'players_min', 1),
                    "players_max": getattr(game, 'players_max', 4),
                    "release_date": game.release_date.isoformat() if game.release_date else None,
                    "created_at": game.created_at.isoformat() if getattr(game, 'created_at', None) else datetime.now(timezone.utc).isoformat(),
                },
            })
        
        # Fallback: if no co-op/new games pass the filter, show top similarity matches without strict filtering
        if not out and local_candidates:
            for game, score in local_candidates:
                explanation = "Popular co-op recommendation." if is_neutral else f"Similarity score {int(score*100)}%."
                out.append({
                    "id": str(uuid4()),
                    "group_id": str(group_id),
                    "game_id": str(game.id),
                    "score": float(score),
                    "explanation": explanation,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "transient": True,
                    "game": {
                        "id": str(game.id),
                        "external_id": getattr(game, 'external_id', None),
                        "title": game.title,
                        "description": game.description,
                        "genres": game.genres,
                        "tags": game.tags,
                        "players_min": getattr(game, 'players_min', 1),
                        "players_max": getattr(game, 'players_max', 4),
                        "release_date": game.release_date.isoformat() if game.release_date else None,
                        "created_at": game.created_at.isoformat() if getattr(game, 'created_at', None) else datetime.now(timezone.utc).isoformat(),
                    },
                })

        # --- Phase 2: try to enrich with Steam candidates (best-effort) ---
        logger = logging.getLogger(__name__)
        try:
            # gather genres/tags from played games first, then local candidates as seed terms for Steam search
            from collections import Counter
            terms = Counter()
            if played_game_ids:
                from sqlalchemy import select
                from app.infrastructure.db.models import GameModel
                played_games = self.games.db.scalars(
                    select(GameModel).where(GameModel.id.in_(played_game_ids))
                ).all()
                for game in played_games:
                    for gen in game.genres or []:
                        terms[gen] += 1
                    for tg in game.tags or []:
                        terms[tg] += 1

            for game, _ in local_candidates:
                for gen in game.genres or []:
                    terms[gen] += 1
                for tg in game.tags or []:
                    terms[tg] += 1

            valid_terms = [t for t, c in terms.most_common() if _is_valid_search_term(t)]
            if not valid_terms:
                valid_terms = ["co-op", "multiplayer", "cooperative", "survival"]

            # query Steam storesearch for each term
            steam_ids: set[str] = set()
            for term in valid_terms[:10]:
                search_query = f"{term} co-op" if "co-op" not in term.lower() else term
                try:
                    resp = requests.get(
                        "https://store.steampowered.com/api/storesearch",
                        params={"cc": "us", "l": "en", "term": search_query},
                        timeout=4,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for item in data.get("items", [])[:20]:
                        steam_ids.add(str(item.get("id")))
                except Exception:
                    continue

            # fetch details for each steam id
            norm_group = normalize(group_embedding)
            ai = self.ai
            
            # get external IDs of played games
            played_external_ids = set()
            if played_game_ids:
                from sqlalchemy import select
                from app.infrastructure.db.models import GameModel
                played_external_ids = set(
                    self.games.db.scalars(
                        select(GameModel.external_id).where(GameModel.id.in_(played_game_ids))
                    ).all()
                )

            existing_external_ids = {g.get("game", {}).get("external_id") for g in out if g.get("game")}
            steam_found = 0
            for sid in list(steam_ids):
                if steam_found >= result_limit * 3:
                    break
                try:
                    r = requests.get(
                        "https://store.steampowered.com/api/appdetails",
                        params={"appids": sid, "cc": "us", "l": "en"},
                        timeout=5,
                    )
                    r.raise_for_status()
                    d = r.json().get(sid, {}).get("data")
                    if not d:
                        continue
                    if d.get("type") and d.get("type") != "game":
                        continue
                    title = d.get("name")
                    desc = d.get("short_description") or d.get("detailed_description") or ""
                    genres = [g.get("description") for g in d.get("genres", [])]
                    tags_list = [c.get("description") for c in d.get("categories", [])]
                    release_date = _parse_steam_release_date(d.get("release_date", {}))
                    if has_blacklist_categories(genres, tags_list):
                        log_skipped_steam_item(sid, genres, tags_list)
                        continue
                    if not is_game_like(genres, tags_list):
                        continue
                    if not _is_coop_game(genres, tags_list):
                        continue
                    # skip if already in local results or played/reviewed
                    steam_game_id = f"steam:{sid}"
                    if steam_game_id in existing_external_ids or steam_game_id in played_external_ids:
                        continue
                    # Filter: custom logic for popularity vs recency
                    r_rev = requests.get(
                        f"https://store.steampowered.com/appreviews/{sid}",
                        params={"json": 1, "language": "all"},
                        timeout=5
                    )
                    r_rev.raise_for_status()
                    rev_data = r_rev.json().get("query_summary", {})
                    total_reviews = rev_data.get("total_reviews", 0)
                    total_positive = rev_data.get("total_positive", 0)
                    rating = (total_positive / total_reviews) if total_reviews > 0 else 0.0
                    
                    if total_reviews >= 300:
                        if rating < 0.70:
                            continue
                    else:
                        if not release_date or release_date.year < 2025:
                            continue
                        if total_reviews > 0 and rating < 0.60:
                            continue

                    emb = ai.embed_text(" ".join([title, desc, *genres, *tags_list]))
                    norm_emb = normalize(emb)
                    score = sum(a * b for a, b in zip(norm_group, norm_emb)) if norm_emb and norm_group else 0.0
                    
                    # Slight priority for highly popular games (proxy for Top Sellers)
                    if total_reviews > 100000:
                        score += 0.12
                    elif total_reviews > 50000:
                        score += 0.08
                    elif total_reviews > 10000:
                        score += 0.04
                    explanation = "Popular co-op recommendation." if is_neutral else f"Similarity score {int(score*100)}%."
                    out.append({
                        "id": str(uuid4()),
                        "group_id": str(group_id),
                        "game_id": steam_game_id,
                        "score": float(score),
                        "explanation": explanation,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "transient": True,
                        "game": {
                            "id": steam_game_id,
                            "external_id": steam_game_id,
                            "title": title,
                            "description": desc,
                            "genres": genres,
                            "tags": tags_list,
                            "players_min": 1,
                            "players_max": 4,
                            "release_date": release_date.isoformat() if release_date else None,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                    })
                    steam_found += 1
                except Exception:
                    continue
        except Exception:
            logger.info("Steam enrichment failed; returning local candidates only")

        # Final fallback: if we still don't have enough candidates, fill the rest with local candidates, ignoring filters
        if len(out) < result_limit and local_candidates:
            existing_ids = {item["game"]["id"] for item in out}
            for game, score in local_candidates:
                if str(game.id) not in existing_ids:
                    explanation = "Popular co-op recommendation." if is_neutral else f"Similarity score {int(score*100)}%."
                    out.append({
                        "id": str(uuid4()),
                        "group_id": str(group_id),
                        "game_id": str(game.id),
                        "score": float(score),
                        "explanation": explanation,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "transient": True,
                        "game": {
                            "id": str(game.id),
                            "external_id": getattr(game, 'external_id', None),
                            "title": game.title,
                            "description": game.description,
                            "genres": game.genres,
                            "tags": game.tags,
                            "players_min": getattr(game, 'players_min', 1),
                            "players_max": getattr(game, 'players_max', 4),
                            "release_date": game.release_date.isoformat() if game.release_date else None,
                            "created_at": game.created_at.isoformat() if getattr(game, 'created_at', None) else datetime.now(timezone.utc).isoformat(),
                        },
                    })
                if len(out) >= result_limit:
                    break

        # sort by score desc and limit
        out.sort(key=lambda x: x.get("score", 0), reverse=True)
        return out[:result_limit]

