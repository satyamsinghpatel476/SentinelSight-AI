from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.security.tokens import AUTH_COOKIE_NAME

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


async def enforce_same_origin_for_cookie_auth(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method.upper() in SAFE_METHODS or not request.url.path.startswith(
        "/api/"
    ):
        return await call_next(request)

    if AUTH_COOKIE_NAME not in request.cookies:
        return await call_next(request)

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    if not origin and not referer:
        return await call_next(request)

    expected_origin = f"{request.url.scheme}://{request.url.netloc}"
    supplied_origin = origin or origin_from_referer(referer)
    if supplied_origin != expected_origin:
        return JSONResponse(
            status_code=403,
            content={"detail": "Cross-origin state-changing request blocked"},
        )

    return await call_next(request)


def origin_from_referer(referer: str | None) -> str | None:
    if not referer:
        return None
    parsed = urlsplit(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"
