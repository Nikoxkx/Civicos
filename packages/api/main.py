"""
CivicOS API — Application entry point.

This is the FastAPI application. It wires together:
- Routers (programs, cities, categories, sources)
- Middleware (structured logging, CORS, error handling)
- Lifespan handlers (database connection pool warmup/shutdown)
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import get_settings
from .routers import categories, cities, programs, sources

logger = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="CivicOS API",
    description=(
        "Open-source civic data intelligence platform. "
        "Ingests, parses, and structures government benefit and housing data "
        "so any city or developer can access it via a clean REST API."
    ),
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# ── CORS — permissive in dev, locked down in production ──────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all error handler. Returns structured JSON errors always."""
    logger.exception("unhandled_error", path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. This has been logged.",
            }
        },
    )


# ── Routers ──────────────────────────────────────────────────────────────
app.include_router(programs.router, prefix="/v1", tags=["programs"])
app.include_router(cities.router, prefix="/v1", tags=["cities"])
app.include_router(categories.router, prefix="/v1", tags=["categories"])
app.include_router(sources.router, prefix="/v1", tags=["sources"])


# ── Health check ─────────────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
async def health_check() -> dict:
    return {"status": "healthy", "version": "0.1.0"}
