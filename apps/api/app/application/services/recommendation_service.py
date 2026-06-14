from uuid import UUID
import logging
from datetime import datetime, timezone

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


def _is_coop_game(genres: list[str], tags: list[str]) -> bool:
    """Check if a game is primarily co-op based on genres and tags."""
    coop_keywords = [
        "co-op", "cooperative", "coop", "multiplayer co-op",
        "online co-op", "local co-op", "split screen", "shared screen",
        "pve co-op", "co-op campaign", "team-based", "cooperative gameplay"
    ]
    all_terms = [t.lower() for t in (genres or []) + (tags or [])]
    
    for term in all_terms:
        for kw in coop_keywords:
            if kw in term:
                return True
    return False


def _is_new_game(release_date: datetime | None) -> bool:
    """Check if a game was released in 2020 or later."""
    if not release_date:
        return False
    return release_date.year >= 2020


def _parse_steam_release_date(release_data: dict) -> datetime | None:
    """Parse release date from Steam API response."""
    if not release_data:
        return None
    # Steam returns release_date as a dict with 'date' and 'coming_soon' fields
    date_str = release_data.get("date")
    coming_soon = release_data.get("coming_soon", False)
    if coming_soon or not date_str:
        return None
    # Date format examples: "Oct 21, 2022", "21 Oct, 2022", "2022-10-21"
    formats = [
        "%b %d, %Y",
        "%d %b, %Y",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%d %B, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


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
        group_embedding = self.profiles.update_group_profile(group_id)
        if not group_embedding:
            return []

        played_game_ids = self.reviews.played_game_ids_for_group(group_id)

        # Simple Steam search approach: use group's known genres/tags collected from games in DB
        # collect genres/tags from group members' reviewed games
        group_genres = set()
        group_tags = set()
        try:
            # inspect reviews for group members' games
            # reviews.list_for_user is used elsewhere; here we query repository rows directly
            # This is a best-effort heuristic: look up recommendations via the reviews repo
            # and gather genres/tags from the games table for those game ids
            # We'll use settings.recommendation_limit * 3 as a search breadth
            search_terms = []
            # fallback to local search if anything fails
            local_candidates = self.games.search_similar(
                embedding=group_embedding,
                exclude_game_ids=played_game_ids,
                limit=(limit or settings.recommendation_limit) * 3,
            )
            # collect genres/tags from local candidates
            for g, _ in local_candidates:
                for gen in g.genres or []:
                    group_genres.add(gen)
                for tg in g.tags or []:
                    group_tags.add(tg)

            # query Steam for each term (genre or tag) to collect app ids
            steam_ids = set()
            for term in list(group_genres)[:3] + list(group_tags)[:3]:
                try:
                    resp = requests.get(
                        "https://store.steampowered.com/api/storesearch",
                        params={"cc": "us", "l": "en", "term": term},
                        timeout=4,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for item in data.get("items", [])[:10]:
                        steam_ids.add(str(item.get("id")))
                except Exception:
                    continue

            # For each steam id, fetch details and create/ensure a Game entry then compute similarity
            repo = GameRepository(self.games.db)
            ai = get_llm_provider()
            for sid in list(steam_ids)[: (limit or settings.recommendation_limit) * 3]:
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
                    embedding = ai.embed_text(" ".join([title, desc, *genres, *tags]))
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
            if _is_coop_game(game.genres, game.tags) and _is_new_game(game.release_date):
                filtered_candidates.append((game, score))
        
        saved: list[RecommendationModel] = []
        for game, score in filtered_candidates:
            explanation = self.ai.explain_recommendation(game=game, score=score)
            saved.append(self.recommendations.upsert(group_id, game.id, score, explanation))
        return saved

    def generate_candidates_for_group(self, group_id: UUID, limit: int | None = None) -> list[dict]:
        """Generate recommendation candidates from Steam without persisting games or recommendations.
        Returns a list of dicts shaped similarly to RecommendationRead but not stored in DB.
        """
        group_embedding = self.profiles.update_group_profile(group_id)
        if not group_embedding:
            return []

        played_game_ids = self.reviews.played_game_ids_for_group(group_id)

        # gather local candidate genres/tags as seed terms
        local_candidates = self.games.search_similar(
            embedding=group_embedding,
            exclude_game_ids=played_game_ids,
            limit=(limit or settings.recommendation_limit) * 3,
        )
        terms = set()
        for g, _ in local_candidates:
            for gen in g.genres or []:
                terms.add(gen)
            for tg in g.tags or []:
                terms.add(tg)

        # query Steam for terms and collect unique app ids
        steam_ids: set[str] = set()
        for term in list(terms)[:6]:
            try:
                resp = requests.get(
                    "https://store.steampowered.com/api/storesearch",
                    params={"cc": "us", "l": "en", "term": term},
                    timeout=4,
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("items", [])[:10]:
                    steam_ids.add(str(item.get("id")))
            except Exception:
                continue

        candidates: list[dict] = []
        logger = logging.getLogger(__name__)
        norm_group = normalize(group_embedding)
        ai = self.ai
        for sid in list(steam_ids)[: (limit or settings.recommendation_limit) * 5]:
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
                # Filter out non-game entries
                if d.get("type") and d.get("type") != "game":
                    continue
                title = d.get("name")
                desc = d.get("short_description") or d.get("detailed_description") or ""
                genres = [g.get("description") for g in d.get("genres", [])]
                tags = [c.get("description") for c in d.get("categories", [])]
                # Parse release date from Steam
                release_date = _parse_steam_release_date(d.get("release_date", {}))
                if has_blacklist_categories(genres, tags):
                    log_skipped_steam_item(sid, genres, tags)
                    continue
                # Heuristic: ensure the Steam entry looks like a game by checking genres/tags
                if not is_game_like(genres, tags):
                    continue
                emb = ai.embed_text(" ".join([title, desc, *genres, *tags]))
                if not emb:
                    continue
                # cosine similarity
                norm_emb = normalize(emb)
                score = sum(a * b for a, b in zip(norm_group, norm_emb)) if norm_emb and norm_group else 0.0
                # Filter for co-op and new games (2020+)
                if not (_is_coop_game(genres, tags) and _is_new_game(release_date)):
                    continue
                explanation = f"Similarity score {int(score*100)}%."
                candidates.append(
                    {
                        "id": str(uuid4()),
                        "group_id": str(group_id),
                        "game_id": f"steam:{sid}",
                        "score": float(score),
                        "explanation": explanation,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        # mark these as transient so callers can detect non-persisted candidates
                        "transient": True,
                        "game": {
                            "id": f"steam:{sid}",
                            "external_id": f"steam:{sid}",
                            "title": title,
                            "description": desc,
                            "genres": genres,
                            "tags": tags,
                            "players_min": 1,
                            "players_max": 4,
                            "release_date": release_date.isoformat() if release_date else None,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                    }
                )
            except Exception:
                continue

        # sort by score desc and limit
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        if not candidates:
            # fallback: return local DB candidates if Steam produced nothing after filtering
            logger.info("Transient generate: steam produced no candidates after filtering; falling back to local DB search")
            local_candidates = self.games.search_similar(
                embedding=group_embedding,
                exclude_game_ids=played_game_ids,
                limit=limit or settings.recommendation_limit,
            )
            out: list[dict] = []
            for game, score in local_candidates:
                # Filter for co-op and new games (2020+)
                if not (_is_coop_game(game.genres, game.tags) and _is_new_game(game.release_date)):
                    continue
                out.append(
                    {
                        "id": str(uuid4()),
                        "group_id": str(group_id),
                        "game_id": str(game.id),
                        "score": float(score),
                        "explanation": f"Similarity score {int(score*100)}%.",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "transient": True,
                        "game": {
                            "id": str(game.id),
                            "external_id": game.external_id,
                            "title": game.title,
                            "description": game.description,
                            "genres": game.genres,
                            "tags": game.tags,
                            "players_min": game.players_min,
                            "players_max": game.players_max,
                            "release_date": game.release_date.isoformat() if game.release_date else None,
                            "created_at": game.created_at.isoformat() if getattr(game, 'created_at', None) else datetime.now(timezone.utc).isoformat(),
                        },
                    }
                )
            return out

        return candidates[: limit or settings.recommendation_limit]

