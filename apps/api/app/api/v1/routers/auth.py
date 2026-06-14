from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.services.auth_service import AuthError, AuthService
from app.infrastructure.db.models import UserModel
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.tokens import RefreshTokenRepository
from app.infrastructure.repositories.users import UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter()


def get_auth_service(db: Session) -> AuthService:
    return AuthService(UserRepository(db), RefreshTokenRepository(db))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    try:
        user, access_token, refresh_token = get_auth_service(db).register(
            payload.email, payload.username, payload.password
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return AuthResponse(user=user, access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    try:
        user, access_token, refresh_token = get_auth_service(db).login(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    db.commit()
    return AuthResponse(user=user, access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    try:
        _, access_token = get_auth_service(db).refresh(payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenPair(access_token=access_token, refresh_token=payload.refresh_token)


@router.get("/me", response_model=UserRead)
def me(current_user: Annotated[UserModel, Depends(get_current_user)]) -> UserModel:
    return current_user

