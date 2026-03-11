"""AgentFlow MVP — FastAPI application entry point."""

import logging
import logging.config
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import create_all
from routes.auth import router as auth_router
from routes.tasks import router as tasks_router
from security import SanitizingFilter, sanitize

# ---------------------------------------------------------------------------
# Logging setup (must happen before any logger usage)
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    """Configure root logger with the sanitizing filter on all handlers."""
    sanitizing_filter = SanitizingFilter()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(sanitizing_filter)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ensure results directory exists
# ---------------------------------------------------------------------------

os.makedirs(settings.RESULTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting AgentFlow backend")
    await create_all()
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down AgentFlow backend")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AgentFlow API",
    version="1.0.0",
    description="Autonomous AI agent task execution platform",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server and production frontend
_allowed_origins: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Allow additional origin from environment (e.g. production domain)
_extra_origin = os.getenv("FRONTEND_URL")
if _extra_origin:
    _allowed_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(tasks_router)

# ---------------------------------------------------------------------------
# Global exception handler — ensure keys never leak in error responses
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    sanitized_detail = sanitize(str(exc))
    logger.error("Unhandled exception: %s", sanitized_detail)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
