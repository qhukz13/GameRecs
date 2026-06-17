from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.services.llm_provider import get_llm_provider
from app.application.services.profile_service import ProfileService
from app.application.services.recommendation_service import RecommendationService
from app.infrastructure.db.models import UserModel
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.games import GameRepository
from app.infrastructure.repositories.groups import GroupRepository
from app.infrastructure.repositories.recommendations import RecommendationRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.infrastructure.repositories.users import UserRepository
from app.schemas.recommendation import RecommendationRead
from app.schemas.game import GameRead

router = APIRouter()
import logging
logger = logging.getLogger(__name__)


def ensure_group_member(groups: GroupRepository, group_id: UUID, user_id: UUID) -> None:
    if not groups.is_member(group_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")


@router.post("/groups/{group_id}/recommendations/generate", response_class=JSONResponse)
def generate_recommendations(
    group_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    persist: bool = Query(False, description="If false, do not persist imported games or recommendations"),
):
    groups = GroupRepository(db)
    ensure_group_member(groups, group_id, current_user.id)
    reviews = ReviewRepository(db)
    service = RecommendationService(
        games=GameRepository(db),
        reviews=reviews,
        recommendations=RecommendationRepository(db),
        profiles=ProfileService(UserRepository(db), groups, reviews),
        ai=get_llm_provider(),
    )
    if not persist:
        # generate candidates without persisting
        candidates = service.generate_candidates_for_group(group_id)
        try:
            logger.info("generate called by user %s for group %s: %d candidates", current_user.id, group_id, len(candidates) if candidates is not None else 0)
        except Exception:
            logger.info("generate called for group %s: candidates=%s", group_id, type(candidates))
        return JSONResponse(content=jsonable_encoder(candidates))
    # persist recommendations (these are ORM models) -> convert to serializable dicts
    recommendations = service.generate_for_group(group_id)
    db.commit()
    # convert ORM recommendation models to dicts suitable for JSON
    out = []
    for r in recommendations:
        # r is RecommendationModel; build a dict matching RecommendationRead
        out.append(
            {
                "id": str(r.id),
                "group_id": str(r.group_id),
                "game_id": str(r.game_id),
                "score": float(r.score),
                "explanation": r.explanation,
                "created_at": r.created_at.isoformat(),
                "game": jsonable_encoder(GameRead.model_validate(r.game)),
            }
        )
    return JSONResponse(content=out)


@router.get("/groups/{group_id}/recommendations", response_model=list[RecommendationRead])
def list_recommendations(
    group_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db)
    ensure_group_member(groups, group_id, current_user.id)
    return RecommendationRepository(db).list_for_group(group_id)


@router.delete("/groups/{group_id}/recommendations", status_code=status.HTTP_204_NO_CONTENT)
def delete_recommendations_for_group(
    group_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db)
    ensure_group_member(groups, group_id, current_user.id)
    RecommendationRepository(db).delete_for_group(group_id)
    db.commit()
    return None


@router.delete("/recommendations/{recommendation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recommendation(
    recommendation_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    # verify that the recommendation belongs to a group the user is a member of
    from app.infrastructure.db.models import RecommendationModel
    rec = db.get(RecommendationModel, recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    groups = GroupRepository(db)
    ensure_group_member(groups, rec.group_id, current_user.id)
    RecommendationRepository(db).delete(recommendation_id)
    db.commit()
    return None

