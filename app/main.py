import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware
from app.routers import auth, users, cached_chat

logger = logging.getLogger(__name__)

_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    openai_ready = bool(settings.openai_api_key)
    anthropic_ready = bool(settings.anthropic_api_key)

    if not openai_ready:
        logger.warning("startup_no_openai_key", extra={"event": "startup_no_openai_key"})
    if not anthropic_ready:
        logger.warning("startup_no_anthropic_key", extra={"event": "startup_no_anthropic_key"})

    logger.info("startup", extra={
        "event": "startup",
        "environment": settings.environment,
        "openai_ready": openai_ready,
        "anthropic_ready": anthropic_ready,
    })
    yield
    logger.info("shutdown", extra={"event": "shutdown"})


_docs_url  = "/docs"  if _settings.environment == "dev" else None
_redoc_url = "/redoc" if _settings.environment == "dev" else None

app = FastAPI(
    title="Retry Logic Gateway API",
    description="Day 16 — Tenacity retry logic on top of Day 15 prompt caching.",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

_cors_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cached_chat.router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
