from fastapi import APIRouter

from app.api.v1.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Add domain routers here as they are implemented, e.g.:
# api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
