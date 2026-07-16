# SentinelSight AI

SentinelSight AI is an AI-assisted web-security monitoring platform for authorized website defacement detection, passive vulnerability assessment, explainable risk scoring and incident response.

## Problem Statement

PS-005 - Website Defacement Detection & Vulnerability Assessment Platform.

## Current Implementation Status

This repository is being built milestone by milestone. Completed scope currently includes the
FastAPI/React foundation, authentication, backend RBAC, organization-scoped user management,
authorized website asset registration, SSRF-safe passive scanning, screenshot capture, baseline
approval, baseline comparison, visual/content change detection, deterministic risk scoring,
automatic incidents, a tamper-evident hash-chained audit trail and a real BYOK AI Incident Analyst.

The deterministic scanner and risk engine are not described as AI. The AI Incident Analyst requires
an evaluator-supplied provider API key configured from the Administrator settings UI.

## AI / Generative AI Disclosure

- SentinelSight uses deterministic security checks for vulnerability findings and risk scoring.
- These deterministic components are not represented as AI.
- Labels in the UI use “Deterministic Risk Score”, “Rule-Based Security Finding” and “AI Incident
  Analysis” to keep that separation clear.
- Generative AI is used only for the AI Incident Analyst feature.
- API credentials are Bring Your Own Key. No organizer, evaluator or team API key is included in
  this repository.
- Administrators configure provider, API key, exact model name/version, optional base URL and
  timeout from Settings → AI Configuration in the frontend.
- API keys are encrypted server-side using key material derived from `APP_SECRET_KEY` and are never
  returned after saving. The UI shows only whether a key exists and the final four characters.
- The exact provider and model used are stored with every generated AI analysis.
- Supported providers: Gemini, OpenAI and OpenAI-compatible providers with a configurable base URL.
- Provider/model tested by the team with a real external key: not tested in this session because no
  user-supplied provider key was available. Automated tests use mocked provider calls and do not
  claim real-provider success.
- AI analysis is advisory and based only on bounded structured scan evidence.
- Core scanning, deterministic risk scoring, findings, baselines, incidents and audit trail work
  without generative AI.
- Frontend-saved organization configuration is the mechanism used for provider calls in this MVP.
  Legacy `AI_*` environment variables are not silently used as a team API key for evaluator
  analysis.

### AI Configuration Demo Steps

1. Log in as Administrator.
2. Open Settings → AI Configuration.
3. Select Gemini, OpenAI or OpenAI-compatible.
4. Enter the evaluator-supplied API key.
5. Enter the exact model name/version.
6. For OpenAI-compatible providers, enter the provider base URL.
7. Click Test Connection to perform a minimal real provider request.
8. Save settings.
9. Open a completed scan or incident.
10. Click Generate AI Analysis and confirm the provider and exact model appear in the result.

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
`AUTO_SEED_DEMO_USERS=true`.

Current verification note: `docker compose config` passes. `docker compose build`, `up`, `ps` and
logs could not be completed from this session because the current user cannot access
`/var/run/docker.sock`, and passwordless sudo is unavailable.

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
- `GET /api/evidence/differences/{scan_id}` serves the generated difference image only after
  authentication and organization ownership checks.

The scanner collects bounded visible text, hashes, response metadata, passive findings and a
Playwright screenshot. When an active approved baseline exists, the next successful scan becomes a
comparison scan and stores title change, visible-text similarity, suspicious phrases, newly
introduced script/iframe domains, screenshot pHash distance, visual change percentage, a highlighted
difference image, calculated risk score and a transparent risk breakdown. Raw target HTML is not
stored or displayed.

## Incident and Audit Workflow

- `GET /api/incidents` lists organization-scoped incidents.
- `GET /api/incidents/{incident_id}` returns an incident with linked scan, findings and notes.
- `PATCH /api/incidents/{incident_id}` changes status, assignment or resolution notes for
  Administrators and Security Analysts.
- `POST /api/incidents/{incident_id}/notes` adds investigation notes for Administrators and Security
  Analysts.
- Viewers can read incidents but cannot modify them.
- `GET /api/audit` lists the organization audit trail.
- `GET /api/audit/verify` verifies the tamper-evident hash chain.

Incidents are created automatically when deterministic scan evidence crosses the configured risk
threshold, when suspicious defacement phrases appear, or when a major visual change and a new script
domain appear together. This is not called blockchain.

## AI Incident Analyst APIs

- `GET /api/ai/config`, `PUT /api/ai/config`, `DELETE /api/ai/config/key` and
  `POST /api/ai/config/test` are Administrator-only.
- `GET /api/ai/status` returns safe non-secret AI availability state.
- `POST /api/scans/{scan_id}/ai-analysis` and
  `POST /api/incidents/{incident_id}/ai-analysis` may be used by Administrators and Security
  Analysts on completed scans/incidents.
- `GET /api/scans/{scan_id}/ai-analysis` and
  `GET /api/incidents/{incident_id}/ai-analysis` allow authenticated organization members to view a
  previously generated analysis.
- Viewer users cannot generate AI analysis.
- AI analysis is never generated automatically for every scan because provider calls may consume
  evaluator quota.

## Controlled Demo Flow

Use only the controlled Docker demo target for the defacement demonstration.

1. Start Docker:
   ```bash
   export APP_SECRET_KEY="replace-with-at-least-32-random-characters"
   export POSTGRES_PASSWORD="replace-with-a-strong-postgres-password"
   export DEMO_TARGET_TOGGLE_SECRET="replace-with-a-demo-toggle-secret"
   export DEMO_ADMIN_EMAIL="admin@example.com"
   export DEMO_ADMIN_PASSWORD="Correct Horse Battery Staple!"
   export DEMO_ANALYST_EMAIL="analyst@example.com"
   export DEMO_ANALYST_PASSWORD="Correct Horse Battery Staple!"
   export DEMO_VIEWER_EMAIL="viewer@example.com"
   export DEMO_VIEWER_PASSWORD="Correct Horse Battery Staple!"
   docker compose up -d --build
   ```
2. Open `http://127.0.0.1:8000` and log in as the Administrator.
3. Add website `http://demo-target:9000` and confirm the authorization checkbox.
4. Ensure the target is normal:
   ```bash
   curl http://127.0.0.1:9000/mode
   curl -X POST \
     -H "X-Demo-Secret: $DEMO_TARGET_TOGGLE_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"mode":"normal"}' \
     http://127.0.0.1:9000/admin/toggle
   ```
5. Run the first scan, open scan details and approve it as the active baseline.
6. Switch the target to defaced mode:
   ```bash
   curl -X POST \
     -H "X-Demo-Secret: $DEMO_TARGET_TOGGLE_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"mode":"defaced"}' \
     http://127.0.0.1:9000/admin/toggle
   ```
7. Run the second scan. It should become a comparison scan.
8. Open the comparison scan and review baseline screenshot, current screenshot, difference image,
   visual change percentage, text similarity, suspicious phrase finding, new script-domain finding,
   risk score and risk breakdown.
9. Open the generated incident, add an investigation note, move it to Investigating, add resolution
   notes and resolve it.
10. Open Audit and verify the hash-chained audit trail.
11. Restore the demo target to normal mode:
   ```bash
   curl -X POST \
     -H "X-Demo-Secret: $DEMO_TARGET_TOGGLE_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"mode":"normal"}' \
     http://127.0.0.1:9000/admin/toggle
   ```

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

## Honest Limitations

- The scanner performs a one-page passive scan only.
- No active exploitation, brute forcing, port scanning or destructive testing is performed.
- Screenshot comparison is heuristic; dynamic websites may create false positives.
- The internal `http://demo-target:9000` exception is development/test-only and rejected in
  production.
- AI remediation may be disabled; deterministic scoring and remediation guidance remain available.
- Only authorized websites may be tested.
