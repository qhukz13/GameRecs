from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.infrastructure.db.models import UserModel
from app.infrastructure.db.session import get_db
from app.infrastructure.repositories.groups import GroupRepository
from app.infrastructure.repositories.users import UserRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.schemas.group import GroupCreate, GroupDetail, GroupInvite, GroupRead
from app.schemas.review import ReviewWithGame
from app.schemas.game import GameRead

router = APIRouter()


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    group = GroupRepository(db).create(payload.name, current_user.id)
    db.commit()
    return group


@router.get("", response_model=list[GroupRead])
def list_groups(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return GroupRepository(db).list_for_user(current_user.id)


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(
    group_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db)
    if not groups.is_member(group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    group = groups.get_with_members(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return GroupDetail(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        created_at=group.created_at,
        members=[membership.user for membership in group.members],
    )


@router.post("/{group_id}/invite", response_model=GroupDetail)
def invite_user(
    group_id: UUID,
    payload: GroupInvite,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db)
    group = groups.get(group_id)
    if not group or group.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    user = UserRepository(db).get_by_username(payload.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    groups.add_member(group_id, user.id)
    db.commit()
    group = groups.get_with_members(group_id)
    return GroupDetail(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        created_at=group.created_at,
        members=[membership.user for membership in group.members],
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db)
    group = groups.get(group_id)
    if not group or group.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    groups.delete(group_id)
    db.commit()
    return None


@router.get("/{group_id}/reviews", response_model=list[ReviewWithGame])
def list_group_reviews(
    group_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db)
    if not groups.is_member(group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return ReviewRepository(db).list_for_group(group_id)


@router.get("/{group_id}/games", response_model=list[GameRead])
def list_group_games(
    group_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    groups = GroupRepository(db)
    if not groups.is_member(group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return groups.list_games(group_id)


