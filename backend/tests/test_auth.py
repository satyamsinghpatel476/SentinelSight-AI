from __future__ import annotations

import asyncio

import httpx

from tests.api_client import with_client
from tests.conftest import SeededUsers

PASSWORD = "Correct Horse Battery Staple!"


async def login(
    client: httpx.AsyncClient, email: str, password: str = PASSWORD
) -> httpx.Response:
    return await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )


def test_valid_login_sets_httponly_cookie_and_me_returns_user(
    seeded_users: SeededUsers,
) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        response = await login(client, seeded_users.admin.email)

        assert response.status_code == 200
        assert response.json()["user"]["email"] == seeded_users.admin.email
        set_cookie = response.headers["set-cookie"]
        assert "sentinelsight_access=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie

        me_response = await client.get("/api/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "administrator"

    asyncio.run(with_client(scenario))


def test_invalid_login_is_rejected(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        response = await login(client, seeded_users.admin.email, "wrong password")

        assert response.status_code == 401
        assert "sentinelsight_access" not in response.cookies

    asyncio.run(with_client(scenario))


def test_inactive_user_cannot_login(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        response = await login(client, seeded_users.inactive.email)

        assert response.status_code == 403

    asyncio.run(with_client(scenario))


def test_logout_clears_auth_cookie(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        login_response = await login(client, seeded_users.admin.email)
        assert login_response.status_code == 200

        logout_response = await client.post("/api/auth/logout")

        assert logout_response.status_code == 200
        assert logout_response.json() == {"status": "logged_out"}
        assert "sentinelsight_access" in logout_response.headers["set-cookie"]
        assert "Max-Age=0" in logout_response.headers["set-cookie"]

    asyncio.run(with_client(scenario))


def test_protected_endpoint_requires_authentication() -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        response = await client.get("/api/auth/me")

        assert response.status_code == 401

    asyncio.run(with_client(scenario))
