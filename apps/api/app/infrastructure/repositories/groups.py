from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.db.models import GroupMemberModel, GroupModel, UserModel


class GroupRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, name: str, owner_id: UUID) -> GroupModel:
        group = GroupModel(name=name, owner_id=owner_id)
        self.db.add(group)
        self.db.flush()
        self.add_member(group.id, owner_id)
        return group

    def get(self, group_id: UUID) -> GroupModel | None:
        return self.db.get(GroupModel, group_id)

    def get_with_members(self, group_id: UUID) -> GroupModel | None:
        return self.db.scalar(
            select(GroupModel)
            .options(selectinload(GroupModel.members).selectinload(GroupMemberModel.user))
            .where(GroupModel.id == group_id)
        )

    def list_for_user(self, user_id: UUID) -> list[GroupModel]:
        return list(
            self.db.scalars(
                select(GroupModel)
                .join(GroupMemberModel)
                .where(GroupMemberModel.user_id == user_id)
                .order_by(GroupModel.created_at.desc())
            )
        )

    def is_member(self, group_id: UUID, user_id: UUID) -> bool:
        member = self.db.get(GroupMemberModel, {"group_id": group_id, "user_id": user_id})
        return member is not None

    def add_member(self, group_id: UUID, user_id: UUID) -> GroupMemberModel:
        member = self.db.get(GroupMemberModel, {"group_id": group_id, "user_id": user_id})
        if member:
            return member
        member = GroupMemberModel(group_id=group_id, user_id=user_id)
        self.db.add(member)
        self.db.flush()
        return member

    def member_users(self, group_id: UUID) -> list[UserModel]:
        return list(
            self.db.scalars(
                select(UserModel).join(GroupMemberModel).where(GroupMemberModel.group_id == group_id)
            )
        )

    def set_profile_embedding(self, group_id: UUID, embedding: list[float] | None) -> None:
        group = self.get(group_id)
        if group:
            group.profile_embedding = embedding
            self.db.flush()

    def delete(self, group_id: UUID) -> None:
        group = self.get(group_id)
        if not group:
            return
        # deleting the group will cascade to members and recommendations via DB FKs
        self.db.delete(group)
        self.db.flush()

