from __future__ import annotations

import asyncio

import httpx
from app.main import app


async def get_json(path: str) -> tuple[int, dict[str, str]]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(path)
    return response.status_code, response.json()


def test_health_endpoint_returns_service_status() -> None:
    status_code, payload = asyncio.run(get_json("/api/health"))

    assert status_code == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "SentinelSight AI"


def test_ready_endpoint_checks_database() -> None:
    status_code, payload = asyncio.run(get_json("/api/ready"))

    assert status_code == 200
    assert payload == {"status": "ready"}
