from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.game import GameRead


class RecommendationRead(BaseModel):
    id: UUID
    group_id: UUID
    game_id: str | UUID
    score: float
    explanation: str
    created_at: datetime
    game: GameRead

    model_config = ConfigDict(from_attributes=True)

