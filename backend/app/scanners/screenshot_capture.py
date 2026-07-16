from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import imagehash
from PIL import Image
from playwright.async_api import Browser, Page, Route, async_playwright

from app.core.config import Settings
from app.security.url_safety import (
    UnsafeUrlError,
    UrlSafetyPolicy,
    validate_url_for_scanning,
)


class ScreenshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScreenshotResult:
    filename: str
    content_type: str
    width: int
    height: int
    perceptual_hash: str


async def capture_screenshot(
    url: str,
    settings: Settings,
    policy: UrlSafetyPolicy,
) -> ScreenshotResult:
    """Capture a bounded browser screenshot after validating all requested URLs."""

    storage_dir = screenshot_storage_dir(settings)
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.png"
    output_path = storage_dir / filename

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        try:
            page = await new_locked_down_page(browser, settings, policy)
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.screenshot_timeout_ms,
            )
            await page.screenshot(path=str(output_path), full_page=False, type="png")
        finally:
            await browser.close()

    return ScreenshotResult(
        filename=filename,
        content_type="image/png",
        width=settings.screenshot_width,
        height=settings.screenshot_height,
        perceptual_hash=perceptual_hash(output_path),
    )


async def new_locked_down_page(
    browser: Browser,
    settings: Settings,
    policy: UrlSafetyPolicy,
) -> Page:
    context = await browser.new_context(
        accept_downloads=False,
        viewport={
            "width": settings.screenshot_width,
            "height": settings.screenshot_height,
        },
    )
    page = await context.new_page()
    page.set_default_navigation_timeout(settings.screenshot_timeout_ms)
    page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))

    async def guarded_route(route: Route) -> None:
        request_url = route.request.url
        if request_url.lower().startswith("file:"):
            await route.abort()
            return
        try:
            validate_url_for_scanning(request_url, policy=policy)
        except UnsafeUrlError:
            await route.abort()
            return
        await route.continue_()

    await page.route("**/*", guarded_route)
    return page


def screenshot_storage_dir(settings: Settings) -> Path:
    return Path(settings.evidence_storage_dir).resolve() / "screenshots"


def screenshot_path_for_filename(settings: Settings, filename: str) -> Path:
    if Path(filename).name != filename:
        raise ScreenshotError("Invalid screenshot filename")
    path = screenshot_storage_dir(settings) / filename
    storage_root = screenshot_storage_dir(settings).resolve()
    resolved = path.resolve()
    if storage_root not in resolved.parents and resolved != storage_root:
        raise ScreenshotError("Invalid screenshot path")
    return resolved


def perceptual_hash(path: Path) -> str:
    with Image.open(path) as image:
        return str(imagehash.phash(image))
