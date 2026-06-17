import logging

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import requests

from uuid import UUID
from pydantic import BaseModel

_log = logging.getLogger(__name__)

from app.api import deps
from app.application.services.recommendation_service import _parse_steam_release_date
from app.infrastructure.repositories.games import GameRepository
from app.schemas.game import GameRead
from app.application.services.llm_provider import get_llm_provider

router = APIRouter()


@router.get("/steam/search")
def steam_search(q: str, db: Session = Depends(deps.get_db)) -> list[dict[str, Any]]:
    """Search Steam store for the given query and return lightweight results."""
    if not q:
        return []
    try:
        resp = requests.get(
            "https://store.steampowered.com/api/storesearch",
            params={"cc": "us", "l": "en", "term": q},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        items = []
        for it in data.get("items", [])[:20]:
            items.append({
                "id": str(it.get("id")),
                "name": it.get("name"),
                "thumb": it.get("tiny_image") or it.get("img"),
            })
        return items
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Steam search failed")


class SteamImportBody(BaseModel):
    id: str
    group_id: UUID | None = None


@router.post("/steam/import", response_model=GameRead)
def steam_import(
    body: SteamImportBody,
    db: Session = Depends(deps.get_db),
    _user=Depends(deps.get_current_user),
):
    """Import a Steam app by its numeric id into the local games table.
    Returns the created GameRead model.
    """
    sid = str(body.id)
    try:
        r = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": sid, "cc": "us", "l": "en"},
            timeout=6,
        )
        
        # Ensure proper indentation for the closing parenthesis
        r.raise_for_status()
        payload = r.json().get(sid, {})
        data = payload.get("data")
        if not data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Steam app not found")
        title = data.get("name")
        desc = data.get("short_description") or data.get("detailed_description") or ""
        genres = [g.get("description") for g in data.get("genres", [])]
        tags = [c.get("description") for c in data.get("categories", [])]

        ai = get_llm_provider()
        embedding = ai.embed_text(" ".join([title, desc, *genres, *tags]))
        release_date = _parse_steam_release_date(data.get("release_date", {}))
        
        # Pass release_date to GameRepository.create

        repo = GameRepository(db)
        from app.infrastructure.repositories.groups import GroupRepository

        # If the game was already imported, return the existing one (idempotent)
        existing = repo.find_by_external_id(f"steam:{sid}")
        if existing:
            if body.group_id:
                GroupRepository(db).add_game(body.group_id, existing.id)
            db.commit()
            return GameRead.model_validate(existing)

        created = repo.create(
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
        if body.group_id:
            GroupRepository(db).add_game(body.group_id, created.id)
        db.commit()
        _log.info("Successfully imported game '%s' (Steam ID: %s)", title, sid)
        return GameRead.model_validate(created)
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            _log.warning("Steam API rate limit exceeded during import for sid=%s", sid)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Steam API rate limit exceeded. Please try again later.",
            )
        _log.exception("Steam API HTTP error during import for sid=%s", sid)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Steam API returned an error: {exc}",
        )
    except Exception as exc:
        _log.exception("Steam import failed for sid=%s", sid)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to import from Steam: {exc}",
        )
