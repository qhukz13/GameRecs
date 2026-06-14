from uuid import UUID

from app.application.services.vector_math import average
from app.infrastructure.repositories.groups import GroupRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.infrastructure.repositories.users import UserRepository


class ProfileService:
    def __init__(
        self,
        users: UserRepository,
        groups: GroupRepository,
        reviews: ReviewRepository,
    ) -> None:
        self.users = users
        self.groups = groups
        self.reviews = reviews

    def update_user_profile(self, user_id: UUID) -> list[float] | None:
        embedding = average(self.reviews.list_embeddings_for_user(user_id))
        self.users.set_profile_embedding(user_id, embedding)
        return embedding

    def update_group_profile(self, group_id: UUID) -> list[float] | None:
        members = self.groups.member_users(group_id)
        embeddings = []
        for member in members:
            pe = member.profile_embedding
            if pe is not None:
                # pgvector may return sequences/arrays; convert safely to list
                embeddings.append(list(pe))
        embedding = average(embeddings)
        self.groups.set_profile_embedding(group_id, embedding)
        return embedding

