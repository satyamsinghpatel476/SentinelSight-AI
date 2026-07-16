# SentinelSight AI

SentinelSight AI is an AI-assisted web-security monitoring platform for authorized website defacement detection, passive vulnerability assessment, explainable risk scoring and incident response.

## Problem Statement

PS-005 - Website Defacement Detection & Vulnerability Assessment Platform.

## Current Implementation Status

This repository is being built milestone by milestone. Completed scope currently includes the
FastAPI/React foundation, authentication, backend RBAC, organization-scoped user management,
authorized website asset registration and scanner-grade URL safety helpers.

Security scanning, baseline approval, screenshot capture, visual/content comparison, incident
workflow, audit logging and AI remediation are intentionally not claimed as complete until their
implementation milestones are finished.

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

The app container runs `alembic upgrade head` before starting Uvicorn. Docker validation was not run
in this workspace because the `docker` CLI is not installed here.

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

## Scanner Safety Boundary

`backend/app/security/url_safety.py` contains the scanner-grade URL validation helper that must be
called immediately before any future HTTP or browser request. It rejects localhost, private IPs,
link-local IPs, reserved ranges, metadata hostnames, metadata IPs, embedded credentials,
unsupported protocols, internal-only hostnames and unsafe redirect targets.

Outbound scanning itself is not implemented yet.

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
