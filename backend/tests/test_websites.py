from __future__ import annotations

import asyncio

import httpx
from app.core.database import SessionLocal
from app.core.enums import WebsiteRiskCategory
from app.models.website_asset import WebsiteAsset
from app.security.url_normalization import normalize_public_url

from tests.api_client import with_client
from tests.conftest import SeededUsers

PASSWORD = "Correct Horse Battery Staple!"


async def login(client: httpx.AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200


def test_url_normalization_accepts_public_http_urls() -> None:
    assert (
        normalize_public_url(" HTTPS://Example.COM:443/a path/?q=1#fragment")
        == "https://example.com/a%20path/?q=1"
    )
    assert normalize_public_url("http://Example.com:80") == "http://example.com/"


def test_admin_can_register_list_update_and_deactivate_website(
    seeded_users: SeededUsers,
) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)

        create_response = await client.post(
            "/api/websites",
            json={
                "name": "Example Site",
                "url": "HTTPS://Example.COM:443/security?q=1#ignore",
                "contact_email": "Security@Example.com",
                "risk_category": "high",
                "monitoring_enabled": True,
                "authorization_confirmed": True,
            },
        )
        assert create_response.status_code == 201
        asset = create_response.json()
        assert asset["normalized_url"] == "https://example.com/security?q=1"
        assert asset["organization_id"] == seeded_users.admin.organization_id

        list_response = await client.get("/api/websites")
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()] == [asset["id"]]

        update_response = await client.patch(
            f"/api/websites/{asset['id']}",
            json={
                "name": "Updated Site",
                "risk_category": "critical",
                "monitoring_enabled": True,
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Site"
        assert update_response.json()["risk_category"] == "critical"

        delete_response = await client.delete(f"/api/websites/{asset['id']}")
        assert delete_response.status_code == 204

        get_response = await client.get(f"/api/websites/{asset['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["monitoring_enabled"] is False

    asyncio.run(with_client(scenario))


def test_registration_requires_authorization_confirmation(
    seeded_users: SeededUsers,
) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)

        response = await client.post(
            "/api/websites",
            json={
                "name": "Unauthorized Site",
                "url": "https://example.org",
                "contact_email": "security@example.org",
                "risk_category": "moderate",
                "monitoring_enabled": True,
                "authorization_confirmed": False,
            },
        )

        assert response.status_code == 422

    asyncio.run(with_client(scenario))


def test_unsafe_registration_urls_are_rejected(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)

        for url in [
            "ftp://example.com",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "https://user:password@example.com",
            "http://",
        ]:
            response = await client.post(
                "/api/websites",
                json={
                    "name": "Blocked Site",
                    "url": url,
                    "contact_email": "security@example.com",
                    "risk_category": "moderate",
                    "monitoring_enabled": True,
                    "authorization_confirmed": True,
                },
            )
            assert response.status_code == 422

    asyncio.run(with_client(scenario))


def test_analyst_and_viewer_cannot_manage_websites(seeded_users: SeededUsers) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.analyst.email)
        analyst_response = await client.post(
            "/api/websites",
            json={
                "name": "Analyst Blocked",
                "url": "https://analyst.example.com",
                "contact_email": "security@example.com",
                "risk_category": "moderate",
                "monitoring_enabled": True,
                "authorization_confirmed": True,
            },
        )
        assert analyst_response.status_code == 403

        await login(client, seeded_users.viewer.email)
        viewer_response = await client.patch(
            "/api/websites/not-real",
            json={"name": "Viewer Blocked"},
        )
        assert viewer_response.status_code == 403

    asyncio.run(with_client(scenario))


def test_websites_are_scoped_to_current_organization(seeded_users: SeededUsers) -> None:
    with SessionLocal() as db:
        asset = WebsiteAsset(
            organization_id=seeded_users.organization_b.id,
            name="Other Org Site",
            url="https://other.example.com",
            normalized_url="https://other.example.com/",
            authorization_confirmed=True,
            monitoring_enabled=True,
            risk_category=WebsiteRiskCategory.high,
            contact_email="security@other.example.com",
            created_by=seeded_users.other_admin.id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        asset_id = asset.id

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)

        get_response = await client.get(f"/api/websites/{asset_id}")
        update_response = await client.patch(
            f"/api/websites/{asset_id}",
            json={"name": "Cross Org Update"},
        )

        assert get_response.status_code == 404
        assert update_response.status_code == 404

    asyncio.run(with_client(scenario))
