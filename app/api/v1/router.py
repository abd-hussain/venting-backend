from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.admin.cms import public_router as cms_public_router
from app.api.v1.auth import router as auth_router
from app.api.v1.listeners import router as listeners_router
from app.api.v1.promo import router as promo_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.ventors import router as ventors_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(ventors_router, prefix="/ventors", tags=["ventors"])
api_router.include_router(listeners_router, prefix="/listeners", tags=["listeners"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(promo_router, prefix="/promo", tags=["promo"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(cms_public_router, prefix="/cms", tags=["cms"])
