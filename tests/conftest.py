"""Shared test fixtures — database, auth client, auth headers."""

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient

# Force test mode — session.py checks for this
os.environ["_"] = "pytest"

# Import after env is set
from backend.db.session import engine  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
async def db_session():
    """Yield a fresh async session for each test, rollback on teardown."""
    from backend.db.session import async_session

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def test_client():
    """HTTPX AsyncClient wired to the FastAPI app (no auth)."""
    from backend.api.server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture()
async def auth_headers(test_client: AsyncClient):
    """Register a test admin user and return Bearer auth headers."""
    import uuid

    email = f"test-{uuid.uuid4().hex[:8]}@test.com"
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "display_name": "Test Admin"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def admin_client(test_client: AsyncClient, auth_headers):
    """An authenticated client with admin role (first user = admin)."""
    test_client.headers.update(auth_headers)
    return test_client
