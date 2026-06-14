from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.game import GameRead


class ReviewCreate(BaseModel):
    game_id: UUID
    rating: int = Field(ge=1, le=10)
    review_text: str = Field(min_length=2)


class ReviewRead(BaseModel):
    id: UUID
    user_id: UUID
    game_id: UUID
    rating: int
    review_text: str
    liked_features: list[str]
    disliked_features: list[str]
    sentiment: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewWithGame(ReviewRead):
    game: GameRead

