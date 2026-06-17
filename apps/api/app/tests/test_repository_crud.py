import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.infrastructure.repositories.games import GameRepository
from app.infrastructure.repositories.reviews import ReviewRepository, DuplicateReviewError
from app.infrastructure.repositories.recommendations import RecommendationRepository
from app.infrastructure.repositories.users import UserRepository
from app.infrastructure.repositories.groups import GroupRepository


def test_game_repository_crud(db_session) -> None:
    repo = GameRepository(db_session)
    
    # Create game
    release_dt = datetime(2023, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    game = repo.create(
        external_id="steam:test_123",
        title="Test Game Title",
        description="A co-op test game description.",
        genres=["action", "co-op"],
        tags=["fun", "survival"],
        players_min=2,
        players_max=4,
        embedding=[0.1] * 8,
        release_date=release_dt
    )
    
    assert game.id is not None
    assert game.title == "Test Game Title"
    assert game.release_date == release_dt
    
    # Get game
    retrieved = repo.get(game.id)
    assert retrieved is not None
    assert retrieved.title == "Test Game Title"
    
    # Find by external ID
    found = repo.find_by_external_id("steam:test_123")
    assert found is not None
    assert found.id == game.id
    
    # List games
    games_list = repo.list()
    assert len(games_list) >= 1
    assert any(g.id == game.id for g in games_list)
    
    # Search similar
    similar = repo.search_similar(embedding=[0.1] * 8, exclude_game_ids=set(), limit=5)
    assert len(similar) >= 1
    assert similar[0][0].id == game.id
    
    # Delete game
    repo.delete(game.id)
    assert repo.get(game.id) is None


def test_review_repository_crud(db_session) -> None:
    user_repo = UserRepository(db_session)
    game_repo = GameRepository(db_session)
    review_repo = ReviewRepository(db_session)
    group_repo = GroupRepository(db_session)

    # Setup dependencies
    user = user_repo.create(
        email=f"tester_{uuid4().hex[:6]}@example.com",
        username=f"tester_{uuid4().hex[:6]}",
        hashed_password="hashed_password"
    )
    game = game_repo.create(
        external_id=f"steam:test_{uuid4().hex[:6]}",
        title="Test Game Title",
        description="A co-op test game description.",
        genres=["action"],
        tags=["fun"],
        players_min=2,
        players_max=4,
        embedding=[0.2] * 8
    )
    group = group_repo.create(name="Test Group", owner_id=user.id)
    
    # Create review
    review = review_repo.create(
        user_id=user.id,
        game_id=game.id,
        rating=8,
        review_text="Awesome gameplay!",
        liked_features=["co-op", "combat"],
        disliked_features=["bugs"],
        sentiment="positive",
        review_embedding=[0.2] * 8
    )
    
    assert review.id is not None
    assert review.rating == 8
    assert review.liked_features == ["co-op", "combat"]
    
    # Duplicate review should fail
    with pytest.raises(DuplicateReviewError):
        review_repo.create(
            user_id=user.id,
            game_id=game.id,
            rating=5,
            review_text="Duplicate review",
            liked_features=[],
            disliked_features=[],
            sentiment="neutral",
            review_embedding=[0.2] * 8
        )
        
    # List for user
    user_reviews = review_repo.list_for_user(user.id)
    assert len(user_reviews) == 1
    assert user_reviews[0].id == review.id
    
    # List for game
    game_reviews = review_repo.list_for_game(game.id)
    assert len(game_reviews) == 1
    assert game_reviews[0].id == review.id
    
    # List embeddings for user
    embeddings = review_repo.list_embeddings_for_user(user.id)
    assert len(embeddings) == 1
    assert embeddings[0] == [0.2] * 8
    
    # Played game ids for group — requires game to be in group_games first
    group_repo.add_game(group.id, game.id)
    played_ids = review_repo.played_game_ids_for_group(group.id)
    assert game.id in played_ids
    
    # Delete review
    review_repo.delete(review.id)
    assert len(review_repo.list_for_user(user.id)) == 0


def test_recommendation_repository_crud(db_session) -> None:
    user_repo = UserRepository(db_session)
    game_repo = GameRepository(db_session)
    group_repo = GroupRepository(db_session)
    rec_repo = RecommendationRepository(db_session)

    # Setup dependencies
    user = user_repo.create(
        email=f"tester_{uuid4().hex[:6]}@example.com",
        username=f"tester_{uuid4().hex[:6]}",
        hashed_password="hashed_password"
    )
    game = game_repo.create(
        external_id=f"steam:test_{uuid4().hex[:6]}",
        title="Test Game Title",
        description="A co-op test game description.",
        genres=["action"],
        tags=["fun"],
        players_min=2,
        players_max=4,
        embedding=[0.3] * 8
    )
    group = group_repo.create(name="Test Group", owner_id=user.id)
    
    # Upsert new recommendation
    rec = rec_repo.upsert(
        group_id=group.id,
        game_id=game.id,
        score=0.85,
        explanation="Perfect fit for the group"
    )
    
    assert rec.id is not None
    assert rec.score == 0.85
    
    # Upsert duplicate recommendation (should update score and explanation)
    updated_rec = rec_repo.upsert(
        group_id=group.id,
        game_id=game.id,
        score=0.95,
        explanation="Even better fit after updates"
    )
    
    assert updated_rec.id == rec.id
    assert updated_rec.score == 0.95
    assert updated_rec.explanation == "Even better fit after updates"
    
    # List for group
    recs = rec_repo.list_for_group(group.id)
    assert len(recs) == 1
    assert recs[0].id == rec.id
    
    # List for user groups
    user_recs = rec_repo.list_for_user_groups([group.id])
    assert len(user_recs) == 1
    assert user_recs[0].id == rec.id
    
    # Delete recommendation
    rec_repo.delete(rec.id)
    assert len(rec_repo.list_for_group(group.id)) == 0
    
    # Test delete for group
    rec_repo.upsert(group_id=group.id, game_id=game.id, score=0.7, explanation="Good fit")
    rec_repo.delete_for_group(group.id)
    assert len(rec_repo.list_for_group(group.id)) == 0


def test_group_repository_games(db_session) -> None:
    user_repo = UserRepository(db_session)
    game_repo = GameRepository(db_session)
    group_repo = GroupRepository(db_session)

    # Setup dependencies
    user = user_repo.create(
        email=f"tester_{uuid4().hex[:6]}@example.com",
        username=f"tester_{uuid4().hex[:6]}",
        hashed_password="hashed_password"
    )
    group = group_repo.create(name="Test Group", owner_id=user.id)
    game1 = game_repo.create(
        external_id=f"steam:test_{uuid4().hex[:6]}",
        title="B Game",
        description="A co-op test game description.",
        genres=["action"],
        tags=["fun"],
        players_min=2,
        players_max=4,
        embedding=[0.2] * 8
    )
    game2 = game_repo.create(
        external_id=f"steam:test_{uuid4().hex[:6]}",
        title="A Game",
        description="A co-op test game description.",
        genres=["action"],
        tags=["fun"],
        players_min=2,
        players_max=4,
        embedding=[0.2] * 8
    )

    # Initially group games should be empty
    assert len(group_repo.list_games(group.id)) == 0

    # Add game1
    group_repo.add_game(group.id, game1.id)
    games = group_repo.list_games(group.id)
    assert len(games) == 1
    assert games[0].id == game1.id

    # Add game2
    group_repo.add_game(group.id, game2.id)
    games = group_repo.list_games(group.id)
    assert len(games) == 2
    # Should be sorted by title ascending: game2 ("A Game") first, then game1 ("B Game")
    assert games[0].id == game2.id
    assert games[1].id == game1.id
