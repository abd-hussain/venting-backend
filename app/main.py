from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure static exists on Heroku (ephemeral FS; may not be in the slug).
    static_dir = Path(settings.static_dir)
    static_dir.mkdir(parents=True, exist_ok=True)
    (static_dir / settings.upload_subdir).mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Legal / Help WebView HTML (same files for all app flavors).
    web_content = Path(__file__).resolve().parent.parent / "docs" / "static-web"
    app.mount(
        "/legal",
        StaticFiles(directory=str(web_content / "legal")),
        name="legal-web",
    )
    app.mount(
        "/help",
        StaticFiles(directory=str(web_content / "help")),
        name="help-web",
    )
    app.mount(
        "/auth",
        StaticFiles(directory=str(web_content / "auth")),
        name="auth-web",
    )

    # Platform / local probes at `/`; versioned API under `/v1`.
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
