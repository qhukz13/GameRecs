from datetime import datetime
from uuid import UUID
from typing import List, Tuple, Set, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import GameModel


class GameRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        external_id: Optional[str],
        title: str,
        description: str,
        genres: List[str],
        tags: List[str],
        players_min: int,
        players_max: int,
        embedding: List[float],
        release_date: Optional[datetime] = None,
    ) -> GameModel:
        game = GameModel(
            external_id=external_id,
            title=title,
            description=description,
            genres=genres,
            tags=tags,
            players_min=players_min,
            players_max=players_max,
            embedding=embedding,
            release_date=release_date,
        )
        self.db.add(game)
        self.db.flush()
        return game

    def get(self, game_id: UUID) -> Optional[GameModel]:
        return self.db.get(GameModel, game_id)
    def list(self) -> List[GameModel]:
        return list(self.db.scalars(select(GameModel).order_by(GameModel.title.asc())))

    def delete(self, game_id: UUID) -> None:
        game = self.get(game_id)
        if not game:
            return
        # Deleting the game will cascade to reviews via SQLAlchemy relationship/DB FK
        self.db.delete(game)
        self.db.flush()

    def search_similar(
        self, embedding: List[float], exclude_game_ids: Set[UUID], limit: int
    ) -> List[Tuple[GameModel, float]]:
        query = select(
            GameModel,
            (1 - GameModel.embedding.cosine_distance(embedding)).label("score"),
        ).where(GameModel.embedding.is_not(None))
        if exclude_game_ids:
            query = query.where(GameModel.id.not_in(exclude_game_ids))
        query = query.order_by(GameModel.embedding.cosine_distance(embedding)).limit(limit)
        return [(row[0], float(row[1])) for row in self.db.execute(query).all()]
