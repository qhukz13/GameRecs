from fastapi import APIRouter

from app.api.v1.routers import auth, dashboard, games, groups, recommendations, reviews, external

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(games.router, prefix="/games", tags=["games"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(recommendations.router, tags=["recommendations"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(external.router, prefix="/external", tags=["external"])

