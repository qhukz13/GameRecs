from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.infrastructure.db.models import UserModel
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.groups import GroupRepository
from app.infrastructure.repositories.recommendations import RecommendationRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.schemas.dashboard import DashboardRead

router = APIRouter()


@router.get("", response_model=DashboardRead)
def dashboard(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db).list_for_user(current_user.id)
    recommendations = RecommendationRepository(db).list_for_user_groups(
        [group.id for group in groups], limit=10
    )
    return DashboardRead(
        groups=groups,
        recent_reviews=ReviewRepository(db).list_for_user(current_user.id, limit=10),
        recommendations=recommendations,
    )

