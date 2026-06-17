from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.services.llm_provider import get_llm_provider
from app.infrastructure.db.models import UserModel
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.games import GameRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.schemas.game import GameCreate, GameRead
from app.schemas.review import ReviewRead

router = APIRouter()


@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
def create_game(
    payload: GameCreate,
    _: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    embedding = get_llm_provider().embed_text(
        " ".join([payload.title, payload.description, *payload.genres, *payload.tags])
    )
    game = GameRepository(db).create(
        external_id=payload.external_id,
        title=payload.title,
        description=payload.description,
        genres=payload.genres,
        tags=payload.tags,
        players_min=payload.players_min,
        players_max=payload.players_max,
        embedding=embedding,
        release_date=payload.release_date,
    )
    if payload.group_id:
        from app.infrastructure.repositories.groups import GroupRepository

        GroupRepository(db).add_game(payload.group_id, game.id)
    db.commit()
    return game


@router.get("", response_model=list[GameRead])
def list_games(
    _: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return GameRepository(db).list()


@router.get("/{game_id}", response_model=GameRead)
def get_game(
    game_id: UUID,
    _: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    game = GameRepository(db).get(game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return game


@router.get("/{game_id}/reviews", response_model=list[ReviewRead])
def game_reviews(
    game_id: UUID,
    _: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not GameRepository(db).get(game_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return ReviewRepository(db).list_for_game(game_id)


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(
    game_id: UUID,
    _: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    repo = GameRepository(db)
    if not repo.get(game_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    repo.delete(game_id)
    db.commit()
    return None
