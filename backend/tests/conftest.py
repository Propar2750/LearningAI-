"""Test fixtures. These run against the real Supabase DB (this is a
connectivity verification suite), seeding the dev graph once per session.

Auth note: the endpoints now require a verified Supabase JWT. Rather than mint
real tokens, tests override the ``get_current_user`` dependency to impersonate a
user. ``DEV_USER_ID`` matches the owner of the seed graph (see ``app/seed.py``)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import CurrentUser, get_current_user
from app.main import app
from app.seed import seed

DEV_USER_ID = "dev-user"  # owner of the seed graph in app/seed.py


@pytest.fixture(scope="session", autouse=True)
async def _seed_db():
    await seed()  # idempotent: skips if g1 already exists


def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
async def client():
    """Signed-in as dev-user, who owns the seed graph."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=DEV_USER_ID, email="dev@test"
    )
    async with _client() as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def anon_client():
    """No auth override — exercises the real dependency (no token => 401)."""
    async with _client() as c:
        yield c


@pytest.fixture
def auth_as():
    """Impersonate an arbitrary user id for the duration of a test."""

    def _set(user_id: str):
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id=user_id, email=None
        )

    yield _set
    app.dependency_overrides.pop(get_current_user, None)
