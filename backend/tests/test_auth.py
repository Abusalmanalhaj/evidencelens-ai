import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@test.com", "password": "securepass1", "full_name": "Jane Doe"},
    )
    assert reg.status_code == 201
    assert reg.json()["email"] == "user@test.com"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@test.com", "password": "securepass1"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "user2@test.com", "password": "securepass1", "full_name": "Jane"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "user2@test.com", "password": "wrongpassword"},
    )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401
