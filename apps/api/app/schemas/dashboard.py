from pydantic import BaseModel

from app.schemas.group import GroupRead
from app.schemas.recommendation import RecommendationRead
from app.schemas.review import ReviewWithGame


class DashboardRead(BaseModel):
    groups: list[GroupRead]
    recent_reviews: list[ReviewWithGame]
    recommendations: list[RecommendationRead]

