"""FastAPI application entry point."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import analyses, auth, health, resumes
from app.config import settings
from app.db import dispose_db, init_db

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    logger.info(
        "%s ready | env=%s | ai=%s",
        settings.app_name,
        settings.environment,
        settings.openai_model if settings.ai_available else "disabled",
    )
    yield
    await dispose_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.1.0",
        description=(
            "Analyses a resume against ATS-compatibility, structure, impact and "
            "job-description matching rules, with an optional AI review layer."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(resumes.router, prefix=settings.api_prefix)
    app.include_router(analyses.router, prefix=settings.api_prefix)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Surface the first validation message plainly, so the UI can show it."""
        errors = exc.errors()
        first = errors[0] if errors else {}
        message = str(first.get("msg", "Invalid request.")).removeprefix("Value error, ")
        field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query"))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": f"{field}: {message}" if field else message,
                "errors": [
                    {"field": ".".join(str(p) for p in e.get("loc", ())), "message": e.get("msg")}
                    for e in errors
                ],
            },
        )

    @app.middleware("http")
    async def hardening(request: Request, call_next):
        """Body-size guard, request id, and baseline security headers."""
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_request_bytes:
            return JSONResponse(
                status_code=413, content={"detail": "Request body is too large."}
            )
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request_id)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith(settings.api_prefix):
            # API responses carry per-user data; never let a shared cache hold them.
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    static_dir = Path(settings.static_dir).resolve() if settings.static_dir else None
    if static_dir is not None and static_dir.is_dir():
        # Production: serve the built frontend from the same origin as the API.
        index_file = static_dir / "index.html"
        assets_dir = static_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        api_root = settings.api_prefix.strip("/")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str) -> FileResponse:
            """Serve real build files; index.html for app routes (SPA fallback)."""
            if full_path == api_root or full_path.startswith(f"{api_root}/"):
                # Unmatched API paths stay JSON 404s, never the app shell.
                raise HTTPException(status_code=404, detail="Not found.")
            candidate = (static_dir / full_path).resolve()
            if full_path and candidate.is_file() and candidate.is_relative_to(static_dir):
                return FileResponse(candidate)
            return FileResponse(index_file)

    else:

        @app.get("/", include_in_schema=False)
        async def root() -> dict[str, str]:
            return {
                "service": settings.app_name,
                "docs": "/docs",
                "health": f"{settings.api_prefix}/health",
            }

    return app


app = create_app()
