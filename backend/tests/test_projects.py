import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_project_crud(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "Acme AI", "description": "Test startup", "sector": "AI", "stage": "Seed"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    get = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert get.status_code == 200
    assert get.json()["name"] == "Acme AI"

    update = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Acme AI Updated"},
        headers=auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Acme AI Updated"

    listing = await client.get("/api/v1/projects", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    delete = await client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_project_access_denied(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "Private", "description": "Test"},
        headers=auth_headers,
    )
    project_id = create.json()["id"]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "other@test.com", "password": "securepass1", "full_name": "Other"},
    )
    other_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "other@test.com", "password": "securepass1"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    resp = await client.get(f"/api/v1/projects/{project_id}", headers=other_headers)
    assert resp.status_code == 403
