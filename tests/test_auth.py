"""Auth API integration tests — register, login, refresh, permissions."""

import pytest


@pytest.mark.asyncio
async def test_register_first_user_is_admin(test_client):
    import uuid

    email = f"admin-{uuid.uuid4().hex[:8]}@test.com"
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "pass1234", "display_name": "Admin"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(test_client):
    import uuid

    email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
    payload = {"email": email, "password": "pass1234"}
    resp1 = await test_client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await test_client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(test_client):
    import uuid

    email = f"login-{uuid.uuid4().hex[:8]}@test.com"
    await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "pass1234"},
    )
    resp = await test_client.post(
        "/api/auth/login",
        json={"email": email, "password": "pass1234"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(test_client):
    import uuid

    email = f"wrongpw-{uuid.uuid4().hex[:8]}@test.com"
    await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct"},
    )
    resp = await test_client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(test_client):
    import uuid

    email = f"refresh-{uuid.uuid4().hex[:8]}@test.com"
    reg = await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "pass1234"},
    )
    refresh_token = reg.json()["refresh_token"]

    resp = await test_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_me_endpoint(test_client, auth_headers):
    resp = await test_client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(test_client):
    resp = await test_client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(test_client):
    resp = await test_client.get("/api/projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_users_requires_admin(test_client, auth_headers):
    resp = await test_client.get("/api/auth/users", headers=auth_headers)
    assert resp.status_code == 200
