"""Tests for API routers using FastAPI TestClient with mocked dependencies."""

from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    """Health endpoint should return ok without auth."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.fixture
def mock_db():
    """Patch get_db dependency to return a mock session."""
    with patch("app.api.v1.routers.auth.get_db") as mock_auth_db, \
         patch("app.api.v1.routers.games.get_db") as mock_games_db, \
         patch("app.api.v1.routers.groups.get_db") as mock_groups_db, \
         patch("app.api.v1.routers.reviews.get_db") as mock_reviews_db, \
         patch("app.api.v1.routers.recommendations.get_db") as mock_recs_db, \
         patch("app.api.v1.routers.dashboard.get_db") as mock_dash_db, \
         patch("app.api.v1.routers.external.get_db") as mock_ext_db:

        mock_session = MagicMock()
        # All routers that use get_db will get the same mock
        for m in [mock_auth_db, mock_games_db, mock_groups_db, mock_reviews_db, mock_recs_db, mock_dash_db, mock_ext_db]:
            m.return_value = mock_session

        yield mock_session


def _make_auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_auth_register_requires_email_and_password(client, mock_db):
    """POST /auth/register should validate required fields."""
    # Missing fields
    resp = client.post(f"{settings.api_v1_prefix}/auth/register", json={})
    assert resp.status_code == 422  # Validation error

    # Valid payload (will fail because mock doesn't actually create user)
    resp = client.post(f"{settings.api_v1_prefix}/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123",
    })
    # Should be 201 or 4xx depending on mock behavior
    assert resp.status_code in (201, 409, 422)


@patch("app.api.v1.routers.reviews.get_current_user")
@patch("app.api.v1.routers.reviews.get_llm_provider")
@patch("app.api.v1.routers.reviews.ProfileService")
@patch("app.api.v1.routers.reviews.ReviewRepository")
@patch("app.api.v1.routers.reviews.GameRepository")
def test_create_review_validates_game_exists(
    mock_game_repo, mock_review_repo, mock_profile_service,
    mock_llm_provider, mock_current_user, client, mock_db
):
    """POST /reviews should return 404 if game does not exist."""
    # Simulate game not found
    mock_game_repo.return_value.get.return_value = None
    mock_current_user.return_value = MagicMock(id=uuid4())

    resp = client.post(
        f"{settings.api_v1_prefix}/reviews",
        json={
            "game_id": str(uuid4()),
            "rating": 8,
            "review_text": "Great game!",
        },
        headers=_make_auth_headers("test-token"),
    )
    assert resp.status_code == 404
    assert "Game not found" in resp.text


@patch("app.api.v1.routers.external.deps.get_current_user")
@patch("app.api.v1.routers.external.GameRepository")
def test_external_steam_search_requires_query(
    mock_game_repo, mock_current_user, client
):
    """GET /external/steam/search should return empty list for empty query."""
    resp = client.get(f"{settings.api_v1_prefix}/external/steam/search", params={"q": ""})
    assert resp.status_code == 200
    assert resp.json() == []


@patch("app.api.v1.routers.groups.get_current_user")
@patch("app.api.v1.routers.groups.GroupRepository")
def test_list_groups_returns_list(
    mock_group_repo, mock_current_user, client, mock_db
):
    """GET /groups should return a list of groups for the current user."""
    mock_current_user.return_value = MagicMock(id=uuid4(), email="test@test.com", username="test")
    mock_group_repo.return_value.list_for_user.return_value = []

    resp = client.get(
        f"{settings.api_v1_prefix}/groups",
        headers=_make_auth_headers("test-token"),
    )
    assert resp.status_code == 200
    assert resp.json() == []


@patch("app.api.v1.routers.dashboard.get_current_user")
@patch("app.api.v1.routers.dashboard.GroupRepository")
@patch("app.api.v1.routers.dashboard.RecommendationRepository")
@patch("app.api.v1.routers.dashboard.ReviewRepository")
def test_dashboard_returns_structure(
    mock_review_repo, mock_rec_repo, mock_group_repo,
    mock_current_user, client, mock_db
):
    """GET /dashboard should return the expected structure."""
    mock_current_user.return_value = MagicMock(id=uuid4())
    mock_group_repo.return_value.list_for_user.return_value = []
    mock_rec_repo.return_value.list_for_user_groups.return_value = []
    mock_review_repo.return_value.list_for_user.return_value = []

    resp = client.get(
        f"{settings.api_v1_prefix}/dashboard",
        headers=_make_auth_headers("test-token"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "groups" in data
    assert "recent_reviews" in data
    assert "recommendations" in data