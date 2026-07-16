from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from app.main import app


async def with_client(callback: Callable[[httpx.AsyncClient], Awaitable[Any]]) -> Any:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await callback(client)
