# SentinelSight AI

SentinelSight AI is an AI-assisted web-security monitoring platform for authorized website defacement detection, passive vulnerability assessment, explainable risk scoring and incident response.

## Problem Statement

PS-005 - Website Defacement Detection & Vulnerability Assessment Platform.

## Current Implementation Status

This repository is being built milestone by milestone. Completed scope currently includes the
FastAPI/React foundation, authentication, backend RBAC, organization-scoped user management,
authorized website asset registration, SSRF-safe passive scanning, screenshot capture and baseline
approval.

Visual comparison, incident workflow, tamper-evident audit-chain verification and AI remediation are
intentionally not claimed as complete until their implementation milestones are finished.

## Technology Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic settings, Alembic, pytest.
- Frontend: React, TypeScript, Vite, React Router, clean reusable CSS.
- Local database: SQLite fallback.
- Container database: PostgreSQL through docker-compose.
- Demo target: small FastAPI service for controlled normal and defaced demo states.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend
npm install
```

## Run Locally

Backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

Demo target:

```bash
cd demo-target
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

## Docker Setup

```bash
docker compose up --build
```

The main platform listens on `http://localhost:8000`. The controlled demo target listens on `http://localhost:9000`.

Docker Compose now requires explicit non-placeholder secrets:

```bash
export APP_SECRET_KEY="replace-with-at-least-32-random-characters"
export POSTGRES_PASSWORD="replace-with-a-strong-postgres-password"
export DEMO_TARGET_TOGGLE_SECRET="replace-with-a-demo-toggle-secret"
docker compose up --build
```

The app container runs `alembic upgrade head` before starting Uvicorn. Docker Compose enables the
controlled local demo-target exception by default and can auto-seed demo users when
`AUTO_SEED_DEMO_USERS=true`. Docker CLI is installed in the current workspace, but full build/runtime
validation was blocked by Docker daemon socket permissions for the current user/session.

## Environment Variables

Copy `.env.example` to `.env` for local development and replace placeholder values. Do not commit real secrets.

## Database Migrations

```bash
cd backend
../.venv/bin/alembic upgrade head
```

SQLite is the default local fallback. Docker Compose configures PostgreSQL through `DATABASE_URL`.

## Seed Demo Users

Set non-placeholder demo passwords in the environment, then run:

```bash
make seed-demo-users
```

The seed script reads `DEMO_ADMIN_EMAIL`, `DEMO_ADMIN_PASSWORD`,
`DEMO_ANALYST_EMAIL`, `DEMO_ANALYST_PASSWORD`, `DEMO_VIEWER_EMAIL` and
`DEMO_VIEWER_PASSWORD`. It refuses placeholder passwords such as `change-me`.

In Docker Compose, `AUTO_SEED_DEMO_USERS` defaults to `true` for local demonstration. The `.env`
example keeps it `false` as a safer default outside the Compose demo path.

## Health Checks

- `GET /api/health` returns application liveness.
- `GET /api/ready` verifies configuration and database connectivity.

## Authentication and RBAC

- `POST /api/auth/login` authenticates an active user and sets an HttpOnly cookie.
- `POST /api/auth/logout` clears the auth cookie.
- `GET /api/auth/me` returns the current authenticated user.
- `GET /api/users` and related user-management endpoints require the Administrator role.
- Security Analysts and Viewers cannot manage users.
- User-management records are scoped by `organization_id`; cross-organization user IDs return 404.

## Website Asset Management

- `GET /api/websites` lists website assets for the current organization.
- `POST /api/websites` registers a website and requires the Administrator role.
- `GET /api/websites/{website_id}` returns an organization-scoped asset.
- `PATCH /api/websites/{website_id}` updates an asset and requires the Administrator role.
- `DELETE /api/websites/{website_id}` disables monitoring for an asset and requires the
  Administrator role.

Website registration requires the authorization confirmation checkbox. Registration-time URL
validation accepts only `http` and `https`, rejects embedded credentials and strips fragments during
normalization. DNS/IP SSRF protections are implemented in the scanner milestone before any outbound
scan requests are enabled.

## Scanning and Baselines

- `POST /api/websites/{website_id}/scans` starts a passive background scan. Administrators and
  Security Analysts may start scans; Viewers may only view scan results.
- `GET /api/websites/{website_id}/scans` lists organization-scoped scan history.
- `GET /api/scans/{scan_id}` returns scan metadata.
- `GET /api/scans/{scan_id}/findings` returns deterministic passive findings.
- `POST /api/scans/{scan_id}/approve-baseline` approves a completed scan as the active trusted
  baseline.
- `GET /api/websites/{website_id}/baseline` returns the active baseline.
- `GET /api/evidence/screenshots/{scan_id}` serves the screenshot only after authentication and
  organization ownership checks.

The scanner collects bounded visible text, hashes, response metadata, passive findings and a
Playwright screenshot. Raw target HTML is not stored or displayed.

## Scanner Safety Boundary

`backend/app/security/url_safety.py` is called immediately before HTTP and browser requests. It
rejects localhost, private IPs, link-local IPs, multicast/reserved/unspecified ranges, metadata
hostnames, metadata IPs, embedded credentials, unsupported protocols, internal-only hostnames and
unsafe redirect targets.

The only internal-host exception is a controlled development/test demo path:

```bash
ALLOW_INTERNAL_DEMO_TARGET=false
DEMO_TARGET_INTERNAL_URL=http://demo-target:9000
```

Production rejects `ALLOW_INTERNAL_DEMO_TARGET=true`. When enabled outside production, only the
exact `http://demo-target:9000` scheme, hostname and port may bypass the internal-host block.
Redirects and browser subresource requests are still revalidated.

## Testing

Backend:

```bash
cd backend
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/pytest
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
npm audit --omit=dev
```

The pytest environment variable prevents unrelated globally installed pytest plugins from being
auto-loaded into this project test run.

## Ethical-Use Notice

SentinelSight AI is intended only for websites an organization owns or is explicitly authorized to monitor. The platform must not be used for unauthorized testing.
