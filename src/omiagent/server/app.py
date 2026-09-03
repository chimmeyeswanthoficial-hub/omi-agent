"""FastAPI app factory: API + gateway + built UI statics."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import Settings, get_settings
from .gateway_routes import router as gateway_router
from .manager import TaskManager
from .routes import router as api_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        _app.state.manager.shutdown()

    app = FastAPI(
        title="OmiAgent",
        version=__version__,
        description=(
            "Self-hosted coding agent + omirouter (`max`) BYOK gateway. "
            "Task API on /api, OpenAI-compatible endpoint on /v1, workspace UI on /."
        ),
        lifespan=lifespan,
    )
    app.state.manager = TaskManager(settings)

    # dev convenience: vite (:5173) talks to :8000 across the origin boundary
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(gateway_router)

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict:

        return {
            "ok": True,
            "version": __version__,
            "sandbox": settings.sandbox,
            "providers": [p.name for p in settings.providers.available()],
            "gateway_auth": bool(settings.gateway_key),
        }

    static = settings.resolved_static_dir
    if static is not None:
        app.mount("/", StaticFiles(directory=str(static), html=True), name="ui")
    else:

        @app.get("/", tags=["meta"], include_in_schema=False)
        async def no_ui() -> dict:
            return {
                "ui": "not built",
                "hint": "run `make build` (or `cd ui && npm install && npm run build`) — "
                "or `make ui-dev` + `make serve` during development",
            }

    return app
