"""FastAPI application entrypoint.

Run with: uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .db import engine
from .routers import graph, health

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ping the DB once at startup so connection problems surface immediately.
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("DB connectivity OK (SELECT 1)")
    except Exception as exc:  # noqa: BLE001 - log and keep serving so /health/db can report it
        logger.error("DB connectivity FAILED: %s: %s", type(exc).__name__, exc)
    yield
    await engine.dispose()


app = FastAPI(title="Learning.AI backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(graph.router)
