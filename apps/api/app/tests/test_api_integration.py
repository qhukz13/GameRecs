from unittest.mock import patch
from uuid import uuid4
from datetime import datetime, timezone

from app.application.services.ai_service import AIService
from app.core.config import settings


def test_full_api_flow(client, db_session) -> None:
    # We patch get_llm_provider to always use the local deterministic AIService
    with patch("app.api.v1.routers.games.get_llm_provider", return_value=AIService()), \
         patch("app.api.v1.routers.reviews.get_llm_provider", return_value=AIService()), \
         patch("app.application.services.recommendation_service.get_llm_provider", return_value=AIService()):
         
        # 1. Register a user
        email = f"user_{uuid4().hex[:6]}@example.com"
        username = f"user_{uuid4().hex[:6]}"
        password = "secret_password"
        
        reg_resp = client.post(
            f"{settings.api_v1_prefix}/auth/register",
            json={"email": email, "username": username, "password": password}
        )
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        assert "access_token" in reg_data
        access_token = reg_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        # 2. Get current user info (GET /auth/me)
        me_resp = client.get(
            f"{settings.api_v1_prefix}/auth/me",
            headers=auth_headers
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email
        
        # 3. Create a group (POST /groups)
        group_name = "Awesome Gamers"
        group_resp = client.post(
            f"{settings.api_v1_prefix}/groups",
            json={"name": group_name},
            headers=auth_headers
        )
        assert group_resp.status_code == 201
        group_data = group_resp.json()
        assert group_data["name"] == group_name
        group_id = group_data["id"]
        
        # 4. Create a game with release_date (POST /games)
        # Verify that release_date is passed and stored correctly
        game_title = "Helldivers 2"
        game_desc = "Awesome online co-op cooperative play PvE shooter with chaos and combat."
        release_date_str = "2024-02-08T00:00:00Z"
        game_resp = client.post(
            f"{settings.api_v1_prefix}/games",
            json={
                "external_id": f"steam:{uuid4().hex[:6]}",
                "title": game_title,
                "description": game_desc,
                "genres": ["Action", "Indie"],
                "tags": ["co-op", "Cooperative", "multiplayer"],
                "players_min": 1,
                "players_max": 4,
                "release_date": release_date_str
            },
            headers=auth_headers
        )
        assert game_resp.status_code == 201
        game_data = game_resp.json()
        assert game_data["title"] == game_title
        assert game_data["release_date"].startswith("2024-02-08")
        game_id = game_data["id"]
        
        # 5. Create a review (POST /reviews) — pass group_id so the game enters group_games
        #    and gets excluded from recommendations (played_game_ids_for_group joins group_games)
        review_resp = client.post(
            f"{settings.api_v1_prefix}/reviews",
            json={
                "game_id": game_id,
                "rating": 9,
                "review_text": "I love this co-op game, very fun combat!",
                "group_id": group_id
            },
            headers=auth_headers
        )
        assert review_resp.status_code == 201
        review_data = review_resp.json()
        print("\n[DEBUG] Created Review:", review_data)
        assert review_data["rating"] == 9
        assert "co-op" in review_data["liked_features"]
        
        # 6. Generate Recommendations (POST /groups/{group_id}/recommendations/generate)
        # Note: Helldivers 2 has release_date in 2024 (>=2020) and has "co-op" tag,
        # so it should pass the strict co-op and new game filters.
        gen_resp = client.post(
            f"{settings.api_v1_prefix}/groups/{group_id}/recommendations/generate?persist=true",
            headers=auth_headers
        )
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()
        assert len(gen_data) >= 1
        
        # 7. Get Recommendations (GET /groups/{group_id}/recommendations)
        get_recs_resp = client.get(
            f"{settings.api_v1_prefix}/groups/{group_id}/recommendations",
            headers=auth_headers
        )
        assert get_recs_resp.status_code == 200
        recs_data = get_recs_resp.json()
        assert len(recs_data) >= 1
        # Helldivers 2 should be excluded because the user has already reviewed/played it
        assert all(r["game"]["title"] != game_title for r in recs_data)

        # 7.5. Get Group Reviews (GET /groups/{group_id}/reviews)
        group_reviews_resp = client.get(
            f"{settings.api_v1_prefix}/groups/{group_id}/reviews",
            headers=auth_headers
        )
        assert group_reviews_resp.status_code == 200
        group_reviews_data = group_reviews_resp.json()
        assert len(group_reviews_data) >= 1
        assert group_reviews_data[0]["game"]["title"] == game_title
        
        # 8. View Dashboard (GET /dashboard)
        dash_resp = client.get(
            f"{settings.api_v1_prefix}/dashboard",
            headers=auth_headers
        )
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()
        assert len(dash_data["groups"]) >= 1
        assert len(dash_data["recent_reviews"]) >= 1
        assert len(dash_data["recommendations"]) >= 1


def test_group_library_flow(client, db_session) -> None:
    from unittest.mock import patch
    from uuid import uuid4
    from app.application.services.ai_service import AIService
    from app.core.config import settings

    # 1. Register a user
    email = f"user_{uuid4().hex[:6]}@example.com"
    username = f"user_{uuid4().hex[:6]}"
    password = "secret_password"
    
    reg_resp = client.post(
        f"{settings.api_v1_prefix}/auth/register",
        json={"email": email, "username": username, "password": password}
    )
    assert reg_resp.status_code == 201
    access_token = reg_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    
    # 2. Create group 1
    g1_resp = client.post(
        f"{settings.api_v1_prefix}/groups",
        json={"name": "Group 1"},
        headers=auth_headers
    )
    assert g1_resp.status_code == 201
    g1_id = g1_resp.json()["id"]

    # 3. Create group 2
    g2_resp = client.post(
        f"{settings.api_v1_prefix}/groups",
        json={"name": "Group 2"},
        headers=auth_headers
    )
    assert g2_resp.status_code == 201
    g2_id = g2_resp.json()["id"]

    # 4. Create a game associated with Group 1
    with patch("app.api.v1.routers.games.get_llm_provider", return_value=AIService()):
        game_resp = client.post(
            f"{settings.api_v1_prefix}/games",
            json={
                "external_id": f"steam:{uuid4().hex[:6]}",
                "title": "Group 1 Exclusive",
                "description": "This game is added to Group 1 library.",
                "genres": ["Action"],
                "tags": ["co-op"],
                "players_min": 2,
                "players_max": 4,
                "group_id": g1_id
            },
            headers=auth_headers
        )
        assert game_resp.status_code == 201
        game_id = game_resp.json()["id"]

    # 5. Fetch library of Group 1
    g1_games_resp = client.get(
        f"{settings.api_v1_prefix}/groups/{g1_id}/games",
        headers=auth_headers
    )
    assert g1_games_resp.status_code == 200
    g1_games = g1_games_resp.json()
    assert len(g1_games) == 1
    assert g1_games[0]["id"] == game_id
    assert g1_games[0]["title"] == "Group 1 Exclusive"

    # 6. Fetch library of Group 2 - should be empty
    g2_games_resp = client.get(
        f"{settings.api_v1_prefix}/groups/{g2_id}/games",
        headers=auth_headers
    )
    assert g2_games_resp.status_code == 200
    assert len(g2_games_resp.json()) == 0

    # 7. Create a review for Group 2 with another game
    with patch("app.api.v1.routers.games.get_llm_provider", return_value=AIService()), \
         patch("app.api.v1.routers.reviews.get_llm_provider", return_value=AIService()):
        # Create a game first without group_id
        game2_resp = client.post(
            f"{settings.api_v1_prefix}/games",
            json={
                "external_id": f"steam:{uuid4().hex[:6]}",
                "title": "Group 2 Review Game",
                "description": "This game is reviewed in Group 2.",
                "genres": ["Action"],
                "tags": ["co-op"],
                "players_min": 2,
                "players_max": 4
            },
            headers=auth_headers
        )
        assert game2_resp.status_code == 201
        game2_id = game2_resp.json()["id"]

        # Create review with group_id pointing to Group 2
        review_resp = client.post(
            f"{settings.api_v1_prefix}/reviews",
            json={
                "game_id": game2_id,
                "rating": 8,
                "review_text": "Good co-op game",
                "group_id": g2_id
            },
            headers=auth_headers
        )
        assert review_resp.status_code == 201

    # 8. Fetch library of Group 2 - should contain Group 2 Review Game
    g2_games_resp = client.get(
        f"{settings.api_v1_prefix}/groups/{g2_id}/games",
        headers=auth_headers
    )
    assert g2_games_resp.status_code == 200
    g2_games = g2_games_resp.json()
    assert len(g2_games) == 1
    assert g2_games[0]["id"] == game2_id
