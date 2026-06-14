from uuid import UUID

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.infrastructure.db.models import UserModel
from app.infrastructure.repositories.tokens import RefreshTokenRepository
from app.infrastructure.repositories.users import UserRepository


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, users: UserRepository, refresh_tokens: RefreshTokenRepository) -> None:
        self.users = users
        self.refresh_tokens = refresh_tokens

    def register(self, email: str, username: str, password: str) -> tuple[UserModel, str, str]:
        if self.users.get_by_email(email):
            raise AuthError("email is already registered")
        if self.users.get_by_username(username):
            raise AuthError("username is already taken")
        user = self.users.create(email=email, username=username, hashed_password=hash_password(password))
        refresh_token = create_refresh_token()
        self.refresh_tokens.create(user.id, refresh_token)
        return user, create_access_token(user.id), refresh_token

    def login(self, email: str, password: str) -> tuple[UserModel, str, str]:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("invalid email or password")
        refresh_token = create_refresh_token()
        self.refresh_tokens.create(user.id, refresh_token)
        return user, create_access_token(user.id), refresh_token

    def refresh(self, token: str) -> tuple[UUID, str]:
        refresh = self.refresh_tokens.get_active(token)
        if not refresh:
            raise AuthError("invalid refresh token")
        return refresh.user_id, create_access_token(refresh.user_id)

