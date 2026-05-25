"""Test fixtures. These run against the real Supabase DB (this is a
connectivity verification suite), seeding the dev graph once per session."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.seed import seed


@pytest.fixture(scope="session", autouse=True)
async def _seed_db():
    await seed()  # idempotent: skips if g1 already exists


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
