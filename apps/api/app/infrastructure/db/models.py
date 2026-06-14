from datetime import UTC, datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.infrastructure.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    owned_groups: Mapped[list["GroupModel"]] = relationship(back_populates="owner")
    reviews: Mapped[list["ReviewModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memberships: Mapped[list["GroupMemberModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class GroupModel(Base):
    __tablename__ = "groups"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    owner: Mapped[UserModel] = relationship(back_populates="owned_groups")
    members: Mapped[list["GroupMemberModel"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["RecommendationModel"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupMemberModel(Base):
    __tablename__ = "group_members"

    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    group: Mapped[GroupModel] = relationship(back_populates="members")
    user: Mapped[UserModel] = relationship(back_populates="memberships")


class GameModel(Base):
    __tablename__ = "games"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    genres: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    players_min: Mapped[int] = mapped_column(Integer, nullable=False)
    players_max: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim))
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    reviews: Mapped[list["ReviewModel"]] = relationship(back_populates="game", cascade="all, delete-orphan")


class ReviewModel(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 10", name="ck_reviews_rating_range"),
        UniqueConstraint("user_id", "game_id", name="uq_review_user_game"),
    )

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    game_id: Mapped[UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    liked_features: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    disliked_features: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)
    review_embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="reviews")
    game: Mapped[GameModel] = relationship(back_populates="reviews")


class RecommendationModel(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("group_id", "game_id", name="uq_recommendation_group_game"),)

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    game_id: Mapped[UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    group: Mapped[GroupModel] = relationship(back_populates="recommendations")
    game: Mapped[GameModel] = relationship()
