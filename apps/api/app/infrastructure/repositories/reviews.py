from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.db.models import GroupMemberModel, ReviewModel


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db


class DuplicateReviewError(Exception):
    """Raised when a user already has a review for the given game."""


    pass


def _ensure_list(x):
    return list(x) if x is not None else []


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        user_id: UUID,
        game_id: UUID,
        rating: int,
        review_text: str,
        liked_features: list[str],
        disliked_features: list[str],
        sentiment: str,
        review_embedding: list[float],
    ) -> ReviewModel:
        # Prevent duplicate reviews for the same user/game to avoid DB integrity errors
        existing = self.db.scalar(
            select(ReviewModel).where(
                ReviewModel.user_id == user_id, ReviewModel.game_id == game_id
            ).limit(1)
        )
        if existing:
            raise DuplicateReviewError("user already reviewed this game")

        review = ReviewModel(
            user_id=user_id,
            game_id=game_id,
            rating=rating,
            review_text=review_text,
            liked_features=_ensure_list(liked_features),
            disliked_features=_ensure_list(disliked_features),
            sentiment=sentiment,
            review_embedding=review_embedding,
        )
        self.db.add(review)
        self.db.flush()
        return review

    def list_for_user(self, user_id: UUID, limit: int | None = None) -> list[ReviewModel]:
        query = (
            select(ReviewModel)
            .options(joinedload(ReviewModel.game))
            .where(ReviewModel.user_id == user_id)
            .order_by(ReviewModel.created_at.desc())
        )
        if limit:
            query = query.limit(limit)
        return list(self.db.scalars(query))

    def list_for_game(self, game_id: UUID) -> list[ReviewModel]:
        return list(
            self.db.scalars(
                select(ReviewModel)
                .where(ReviewModel.game_id == game_id)
                .order_by(ReviewModel.created_at.desc())
            )
        )

    def list_embeddings_for_user(self, user_id: UUID) -> list[list[float]]:
        reviews = self.db.scalars(
            select(ReviewModel).where(
                ReviewModel.user_id == user_id,
                ReviewModel.review_embedding.is_not(None),
            )
        )
        return [list(review.review_embedding) for review in reviews]

    def played_game_ids_for_group(self, group_id: UUID) -> set[UUID]:
        rows = self.db.scalars(
            select(ReviewModel.game_id)
            .join(GroupMemberModel, GroupMemberModel.user_id == ReviewModel.user_id)
            .where(GroupMemberModel.group_id == group_id)
        )
        return set(rows)

    def delete(self, review_id: UUID) -> None:
        review = self.db.get(ReviewModel, review_id)
        if not review:
            return
        self.db.delete(review)
        self.db.flush()

