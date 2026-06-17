from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.services.llm_provider import get_llm_provider
from app.application.services.profile_service import ProfileService
from app.infrastructure.db.models import UserModel
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.games import GameRepository
from app.infrastructure.repositories.groups import GroupRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.infrastructure.repositories.users import UserRepository
from app.schemas.review import ReviewCreate, ReviewRead, ReviewWithGame

router = APIRouter()


@router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    game = GameRepository(db).get(payload.game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Game not found")
    ai = get_llm_provider()
    analysis = ai.analyze_review(payload.review_text, payload.rating)
    reviews = ReviewRepository(db)
    try:
        review = reviews.create(
        user_id=current_user.id,
        game_id=payload.game_id,
        rating=payload.rating,
        review_text=payload.review_text,
        liked_features=analysis.liked_features,
        disliked_features=analysis.disliked_features,
        sentiment=analysis.sentiment,
        review_embedding=analysis.embedding,
        )
    except Exception as exc:
        # translate duplicate review repository error to HTTP 409
        from app.infrastructure.repositories.reviews import DuplicateReviewError

        if isinstance(exc, DuplicateReviewError):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        raise
    ProfileService(UserRepository(db), GroupRepository(db), reviews).update_user_profile(current_user.id)
    if payload.group_id:
        GroupRepository(db).add_game(payload.group_id, payload.game_id)
    db.commit()
    return review


@router.get("/me", response_model=list[ReviewWithGame])
def my_reviews(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return ReviewRepository(db).list_for_user(current_user.id)


@router.get("/games/{game_id}", response_model=list[ReviewRead])
def game_reviews(
    game_id: UUID,
    _: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return ReviewRepository(db).list_for_game(game_id)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    reviews = ReviewRepository(db)
    from app.infrastructure.db.models import ReviewModel

    rev = db.get(ReviewModel, review_id)
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if rev.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    reviews.delete(review_id)
    # update user profile embeddings after deletion
    ProfileService(UserRepository(db), GroupRepository(db), reviews).update_user_profile(current_user.id)
    db.commit()
    return None

