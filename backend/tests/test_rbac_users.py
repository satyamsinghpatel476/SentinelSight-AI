from __future__ import annotations

import asyncio

import httpx

from tests.api_client import with_client
from tests.conftest import SeededUsers

PASSWORD = "Correct Horse Battery Staple!"


async def login(client: httpx.AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200


def test_admin_can_manage_users(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)

        create_response = await client.post(
            "/api/users",
            json={
                "name": "New Viewer",
                "email": "new-viewer@example.com",
                "password": "Another Strong Password!",
                "role": "viewer",
                "is_active": True,
            },
        )
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user["organization_id"] == seeded_users.admin.organization_id

        role_response = await client.patch(
            f"/api/users/{created_user['id']}/role",
            json={"role": "security_analyst"},
        )
        assert role_response.status_code == 200
        assert role_response.json()["role"] == "security_analyst"

    asyncio.run(with_client(scenario))


def test_analyst_cannot_manage_users(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.analyst.email)

        response = await client.get("/api/users")

        assert response.status_code == 403

    asyncio.run(with_client(scenario))


def test_viewer_cannot_manage_users(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.viewer.email)

        response = await client.post(
            "/api/users",
            json={
                "name": "Blocked User",
                "email": "blocked@example.com",
                "password": "Another Strong Password!",
                "role": "viewer",
            },
        )

        assert response.status_code == 403

    asyncio.run(with_client(scenario))


def test_user_management_is_scoped_to_current_organization(
    seeded_users: SeededUsers,
) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)

        get_response = await client.get(f"/api/users/{seeded_users.other_admin.id}")
        patch_response = await client.patch(
            f"/api/users/{seeded_users.other_admin.id}/status",
            json={"is_active": False},
        )

        assert get_response.status_code == 404
        assert patch_response.status_code == 404

    asyncio.run(with_client(scenario))
