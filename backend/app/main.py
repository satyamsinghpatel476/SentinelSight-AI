from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.scans import router as scans_router
from app.api.users import router as users_router
from app.api.websites import router as websites_router
from app.core.config import get_settings
from app.core.csrf import enforce_same_origin_for_cookie_auth
from app.core.request_limits import enforce_request_body_limit
from app.core.security_headers import add_security_headers

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_runtime_security()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.middleware("http")(add_security_headers)
    app.middleware("http")(enforce_same_origin_for_cookie_auth)
    app.middleware("http")(enforce_request_body_limit)
    app.include_router(auth_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(scans_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(websites_router, prefix="/api")

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False, response_model=None)
    async def index() -> FileResponse | dict[str, str]:
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"service": settings.app_name, "status": "frontend_not_built"}

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def spa_fallback(
        full_path: str,
    ) -> FileResponse | JSONResponse | dict[str, str]:
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"service": settings.app_name, "status": "frontend_not_built"}

    return app


app = create_app()
