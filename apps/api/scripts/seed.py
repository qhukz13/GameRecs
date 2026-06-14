from sqlalchemy import select

from datetime import datetime, timezone

from app.application.services.llm_provider import get_llm_provider
from app.application.services.auth_service import AuthService
from app.application.services.profile_service import ProfileService
from app.application.services.recommendation_service import RecommendationService
from app.infrastructure.db.models import GameModel, ReviewModel, UserModel
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.games import GameRepository
from app.infrastructure.repositories.groups import GroupRepository
from app.infrastructure.repositories.recommendations import RecommendationRepository
from app.infrastructure.repositories.reviews import ReviewRepository
from app.infrastructure.repositories.tokens import RefreshTokenRepository
from app.infrastructure.repositories.users import UserRepository


USERS = [
    ("alex@example.com", "alex", "password123"),
    ("mira@example.com", "mira", "password123"),
    ("sam@example.com", "sam", "password123"),
]

GAMES = [
    {
        "external_id": "steam:548430",
        "title": "Deep Rock Galactic",
        "description": "Four player co-op mining with combat, survival pressure, and chaotic extraction.",
        "genres": ["action", "survival"],
        "tags": ["combat", "chaos", "co-op"],
        "players_min": 1,
        "players_max": 4,
        "release_date": datetime(2022, 1, 13, tzinfo=timezone.utc),
    },
    {
        "external_id": "steam:620",
        "title": "Portal 2",
        "description": "Two player puzzle co-op with timing, communication, and spatial problem solving.",
        "genres": ["puzzle"],
        "tags": ["puzzle", "strategy", "casual"],
        "players_min": 2,
        "players_max": 2,
        "release_date": datetime(2011, 4, 19, tzinfo=timezone.utc),
    },
    {
        "external_id": "steam:892970",
        "title": "Valheim",
        "description": "Co-op survival sandbox with building, exploration, combat, and long-term progression.",
        "genres": ["survival", "sandbox"],
        "tags": ["building", "survival", "combat", "co-op"],
        "players_min": 1,
        "players_max": 10,
        "release_date": datetime(2021, 2, 2, tzinfo=timezone.utc),
    },
    {
        "external_id": "steam:1097150",
        "title": "It Takes Two",
        "description": "Story-driven co-op adventure with puzzles, platforming, and constant mechanical variety.",
        "genres": ["adventure", "puzzle"],
        "tags": ["story", "puzzle", "casual", "co-op"],
        "players_min": 2,
        "players_max": 2,
        "release_date": datetime(2021, 3, 26, tzinfo=timezone.utc),
    },
]

REVIEWS = [
    ("alex@example.com", "Deep Rock Galactic", 9, "Great combat and chaos. The survival pressure is fun."),
    ("mira@example.com", "Portal 2", 9, "Loved the puzzle strategy and casual pace for a two player night."),
    ("sam@example.com", "Valheim", 8, "Building and survival are excellent, combat is best with friends."),
]


def main() -> None:
    db = SessionLocal()
    try:
        users = UserRepository(db)
        tokens = RefreshTokenRepository(db)
        auth = AuthService(users, tokens)
        for email, username, password in USERS:
            if not users.get_by_email(email):
                auth.register(email, username, password)

        ai = get_llm_provider()
        games = GameRepository(db)
        for payload in GAMES:
            existing = db.scalar(select(GameModel).where(GameModel.external_id == payload["external_id"]))
            if not existing:
                games.create(
                    external_id=payload["external_id"],
                    title=payload["title"],
                    description=payload["description"],
                    genres=payload["genres"],
                    tags=payload["tags"],
                    players_min=payload["players_min"],
                    players_max=payload["players_max"],
                    embedding=ai.embed_text(
                        " ".join([payload["title"], payload["description"], *payload["genres"], *payload["tags"]])
                    ),
                    release_date=payload["release_date"],
                )

        group_repo = GroupRepository(db)
        alex = users.get_by_email("alex@example.com")
        group = db.scalar(select(UserModel).where(UserModel.email == "alex@example.com"))
        if alex:
            existing_groups = group_repo.list_for_user(alex.id)
            seed_group = next((item for item in existing_groups if item.name == "Friday Co-op"), None)
            if not seed_group:
                seed_group = group_repo.create("Friday Co-op", alex.id)
            for email, _, _ in USERS:
                user = users.get_by_email(email)
                if user:
                    group_repo.add_member(seed_group.id, user.id)

        review_repo = ReviewRepository(db)
        profile_service = ProfileService(users, group_repo, review_repo)
        for email, title, rating, text in REVIEWS:
            user = users.get_by_email(email)
            game_model = db.scalar(select(GameModel).where(GameModel.title == title))
            if not user or not game_model:
                continue
            existing_review = db.scalar(
                select(ReviewModel).where(
                    ReviewModel.user_id == user.id,
                    ReviewModel.game_id == game_model.id,
                )
            )
            if existing_review:
                continue
            analysis = ai.analyze_review(text, rating)
            review_repo.create(
                user_id=user.id,
                game_id=game_model.id,
                rating=rating,
                review_text=text,
                liked_features=analysis.liked_features,
                disliked_features=analysis.disliked_features,
                sentiment=analysis.sentiment,
                review_embedding=analysis.embedding,
            )
            profile_service.update_user_profile(user.id)

        if alex:
            seed_group = next(
                (item for item in group_repo.list_for_user(alex.id) if item.name == "Friday Co-op"),
                None,
            )
            if seed_group:
                RecommendationService(
                    games=games,
                    reviews=review_repo,
                    recommendations=RecommendationRepository(db),
                    profiles=profile_service,
                    ai=ai,
                ).generate_for_group(seed_group.id)

        db.commit()
        print("Seed data created. Login with alex@example.com / password123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
