"""Aggregate router for the admin portal API."""

from fastapi import APIRouter

from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.auth import router as auth_router
from app.api.v1.admin.catalogs import router as catalogs_router
from app.api.v1.admin.cms import router as cms_router
from app.api.v1.admin.config import router as config_router
from app.api.v1.admin.help import router as help_router
from app.api.v1.admin.legal import router as legal_router
from app.api.v1.admin.listeners import router as listeners_router
from app.api.v1.admin.notes import router as notes_router
from app.api.v1.admin.notifications import router as notifications_router
from app.api.v1.admin.payouts import router as payouts_router
from app.api.v1.admin.reports import router as reports_router
from app.api.v1.admin.rewards import router as rewards_router
from app.api.v1.admin.sessions import router as sessions_router
from app.api.v1.admin.staff import router as staff_router
from app.api.v1.admin.stats import router as stats_router
from app.api.v1.admin.training import router as training_router
from app.api.v1.admin.users import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(listeners_router)
router.include_router(reports_router)
router.include_router(notes_router)
router.include_router(payouts_router)
router.include_router(catalogs_router)
router.include_router(legal_router)
router.include_router(help_router)
router.include_router(stats_router)
router.include_router(analytics_router)
router.include_router(sessions_router)
router.include_router(notifications_router)
router.include_router(config_router)
router.include_router(cms_router)
router.include_router(staff_router)
router.include_router(rewards_router)
router.include_router(training_router)
