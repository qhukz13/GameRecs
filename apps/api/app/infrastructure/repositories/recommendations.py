from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.db.models import RecommendationModel


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(
        self, group_id: UUID, game_id: UUID, score: float, explanation: str
    ) -> RecommendationModel:
        existing = self.db.scalar(
            select(RecommendationModel).where(
                RecommendationModel.group_id == group_id,
                RecommendationModel.game_id == game_id,
            )
        )
        if existing:
            existing.score = score
            existing.explanation = explanation
            self.db.flush()
            return existing
        recommendation = RecommendationModel(
            group_id=group_id,
            game_id=game_id,
            score=score,
            explanation=explanation,
        )
        self.db.add(recommendation)
        self.db.flush()
        return recommendation

    def list_for_group(self, group_id: UUID) -> list[RecommendationModel]:
        return list(
            self.db.scalars(
                select(RecommendationModel)
                .options(joinedload(RecommendationModel.game))
                .where(RecommendationModel.group_id == group_id)
                .order_by(RecommendationModel.score.desc())
            )
        )

    def list_for_user_groups(self, group_ids: list[UUID], limit: int = 10) -> list[RecommendationModel]:
        if not group_ids:
            return []
        return list(
            self.db.scalars(
                select(RecommendationModel)
                .options(joinedload(RecommendationModel.game))
                .where(RecommendationModel.group_id.in_(group_ids))
                .order_by(RecommendationModel.score.desc())
                .limit(limit)
            )
        )

    def delete_for_group(self, group_id: UUID) -> None:
        # remove all recommendations for a group (used when regenerating or cleaning)
        rows = self.db.scalars(select(RecommendationModel).where(RecommendationModel.group_id == group_id))
        for r in rows:
            self.db.delete(r)
        self.db.flush()

    def delete(self, recommendation_id: UUID) -> None:
        rec = self.db.get(RecommendationModel, recommendation_id)
        if not rec:
            return
        self.db.delete(rec)
        self.db.flush()

