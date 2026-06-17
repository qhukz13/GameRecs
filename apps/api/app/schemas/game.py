from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GameCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    players_min: int = Field(ge=1)
    players_max: int = Field(ge=1)
    release_date: datetime | None = None
    group_id: UUID | None = None

    @model_validator(mode="after")
    def validate_players(self) -> "GameCreate":
        if self.players_max < self.players_min:
            raise ValueError("players_max must be greater than or equal to players_min")
        return self


class GameRead(BaseModel):
    id: str | UUID
    external_id: str | None
    title: str
    description: str
    genres: list[str]
    tags: list[str]
    players_min: int
    players_max: int
    release_date: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
