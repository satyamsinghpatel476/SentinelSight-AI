from __future__ import annotations

import os
from enum import StrEnum

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="SentinelSight AI Controlled Demo Target")


class DemoMode(StrEnum):
    normal = "normal"
    defaced = "defaced"


class ToggleRequest(BaseModel):
    mode: DemoMode


current_mode = DemoMode.normal


def security_headers(mode: DemoMode) -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    if mode == DemoMode.normal:
        headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'"
        )
    return headers


def normal_page() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Northstar Community Credit Union</title>
        <style>
          body {
            margin: 0;
            font-family: Arial, sans-serif;
            color: #1f2937;
            background: #f8fafc;
          }
          header { background: #0f766e; color: white; padding: 32px 48px; }
          nav { display: flex; gap: 20px; margin-bottom: 36px; font-weight: 700; }
          main { padding: 48px; }
          .panel {
            max-width: 880px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            background: white;
            padding: 32px;
          }
          h1 { margin: 0 0 12px; font-size: 40px; }
          p { line-height: 1.6; }
        </style>
      </head>
      <body>
        <header>
          <nav aria-label="Demo target navigation">
            <span>Accounts</span>
            <span>Business</span>
            <span>Security Center</span>
            <span>Contact</span>
          </nav>
          <h1>Banking services for growing communities</h1>
          <p>Secure digital tools, local support and practical financial guidance.</p>
        </header>
        <main>
          <section class="panel">
            <h2>Member security notice</h2>
            <p>
              We use standard security headers and monitored deployment checks
              for this controlled demonstration site.
            </p>
          </section>
        </main>
      </body>
    </html>
    """


def defaced_page() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Hacked by Demo Attacker</title>
        <style>
          body {
            margin: 0;
            font-family: Arial, sans-serif;
            color: #111827;
            background: #fff1f2;
          }
          header { background: #7f1d1d; color: white; padding: 44px 48px; }
          main { padding: 48px; }
          .warning {
            max-width: 880px;
            border: 3px solid #ef4444;
            border-radius: 8px;
            background: white;
            padding: 32px;
          }
          h1 { margin: 0 0 12px; font-size: 44px; }
          p { line-height: 1.6; }
        </style>
        <script type="application/json" id="simulated-unknown-script">
          {
            "src": "https://demo-unknown-script.invalid/app.js",
            "note": "Simulated reference only. Not executed."
          }
        </script>
      </head>
      <body>
        <header>
          <h1>Hacked by Demo Attacker</h1>
          <p>
            This is a controlled test-only defacement state for SentinelSight AI
            demonstrations.
          </p>
        </header>
        <main>
          <section class="warning">
            <h2>Site defaced demonstration</h2>
            <p>
              No real malicious code is served. This page exists only to
              validate authorized detection workflows.
            </p>
          </section>
        </main>
      </body>
    </html>
    """


@app.get("/")
async def home() -> Response:
    content = normal_page() if current_mode == DemoMode.normal else defaced_page()
    return Response(
        content=content, media_type="text/html", headers=security_headers(current_mode)
    )


@app.get("/mode")
async def mode() -> dict[str, str]:
    return {"mode": current_mode}


@app.post("/admin/toggle")
async def toggle_mode(
    payload: ToggleRequest,
    x_demo_secret: str | None = Header(default=None),
) -> dict[str, str]:
    expected_secret = os.getenv("DEMO_TARGET_TOGGLE_SECRET", "").strip()
    if not expected_secret or expected_secret == "change-me":
        raise HTTPException(
            status_code=503,
            detail="Demo target toggle is not configured",
        )
    if not x_demo_secret or x_demo_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid demo target secret")

    global current_mode
    current_mode = payload.mode
    return {"mode": current_mode}
