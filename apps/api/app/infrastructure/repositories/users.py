from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import UserModel


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: UUID) -> UserModel | None:
        return self.db.get(UserModel, user_id)

    def get_by_email(self, email: str) -> UserModel | None:
        return self.db.scalar(select(UserModel).where(UserModel.email == email.lower()))

    def get_by_username(self, username: str) -> UserModel | None:
        return self.db.scalar(select(UserModel).where(UserModel.username == username))

    def create(self, email: str, username: str, hashed_password: str) -> UserModel:
        user = UserModel(email=email.lower(), username=username, hashed_password=hashed_password)
        self.db.add(user)
        self.db.flush()
        return user

    def set_profile_embedding(self, user_id: UUID, embedding: list[float] | None) -> None:
        user = self.get(user_id)
        if user:
            user.profile_embedding = embedding
            self.db.flush()

