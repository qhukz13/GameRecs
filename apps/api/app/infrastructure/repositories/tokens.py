from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_token
from app.infrastructure.db.models import RefreshTokenModel


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user_id: UUID, token: str) -> RefreshTokenModel:
        refresh = RefreshTokenModel(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
        self.db.add(refresh)
        self.db.flush()
        return refresh

    def get_active(self, token: str) -> RefreshTokenModel | None:
        now = datetime.now(UTC)
        return self.db.scalar(
            select(RefreshTokenModel).where(
                RefreshTokenModel.token_hash == hash_token(token),
                RefreshTokenModel.revoked_at.is_(None),
                RefreshTokenModel.expires_at > now,
            )
        )

    def revoke(self, token: str) -> None:
        refresh = self.get_active(token)
        if refresh:
            refresh.revoked_at = datetime.now(UTC)
            self.db.flush()

