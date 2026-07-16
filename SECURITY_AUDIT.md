# SentinelSight AI Security Audit

Date: 2026-07-16
Reviewer stance: independent application-security reviewer and hackathon judge.

## Scope Reviewed

- Implemented backend APIs: health, auth, users, website assets, scans, findings, baselines,
  screenshot/difference evidence, incidents, audit verification and AI configuration/analysis.
- Implemented frontend: foundation dashboard, login/logout, website list/add/detail, scan polling,
  baseline approval, scan detail, incident workflow, audit page and Administrator AI settings.
- Demo target service.
- Docker and deployment configuration.
- Tests, README, progress and limitations documentation.

## Critical Findings

### C-01: PS-005 End-to-End Workflow Is Not Implemented

Status: fixed for the hackathon MVP scope.

The first audit found that the required baseline-to-defacement-to-incident scenario did not work
because these major systems were missing:

- Visual/content comparison.
- Risk engine.
- Incident creation and workflow.
- Tamper-evident audit chain.
- AI remediation provider abstraction.

Fix: implemented baseline comparison, title/text/domain checks, suspicious phrase detection,
visual pHash and changed-pixel comparison, generated difference images, deterministic risk scoring,
automatic incident creation, incident status/notes workflow and hash-chain audit verification.

Follow-up fix: Milestone 8 implements a real BYOK AI Incident Analyst with Gemini, OpenAI and
OpenAI-compatible providers. No fake AI output is generated and deterministic checks are still not
called AI.

## High Findings

### H-01: Production Secret and Cookie Hardening Were Not Enforced

Status: fixed.

`APP_SECRET_KEY` defaulted to `change-me`, and production startup did not reject weak/default
secrets or insecure cookies. A weak JWT signing key would allow token forgery.

Fix: added runtime production validation for `APP_SECRET_KEY` and `COOKIE_SECURE`.

### H-02: Docker Runtime Did Not Apply Database Migrations

Status: fixed.

The production container started Uvicorn directly. Fresh PostgreSQL deployments would boot without
tables, breaking login, users and website asset APIs.

Fix: container startup now runs `alembic upgrade head` before starting Uvicorn.

### H-03: Demo Target Toggle Secret Had an Unsafe Default

Status: fixed.

The demo target accepted `change-me` as a valid toggle secret when unset/defaulted. Anyone who knew
the default could switch the controlled target into defaced mode.

Fix: the toggle endpoint now refuses missing or placeholder secrets. Docker Compose now requires
`DEMO_TARGET_TOGGLE_SECRET`.

### H-04: Scanner-Grade SSRF Validation Module Was Missing

Status: fixed and integrated with the passive scanner.

Registration-time URL validation existed, but scanner-grade DNS/IP validation did not. If outbound
scanning were added without this boundary, localhost, private IPs, link-local addresses and metadata
services could be reachable.

Fix: added `backend/app/security/url_safety.py` with DNS resolution, IP classification,
metadata-host blocking, internal-hostname blocking and redirect-target validation helpers. Milestone
4 now calls this boundary before HTTP requests, redirect follow-up requests and Playwright browser
requests.

### H-05: Cookie-Authenticated Mutating API Requests Had No Origin Check

Status: fixed.

The app uses HttpOnly cookie authentication. SameSite=Lax is helpful but should not be the only CSRF
control for state-changing API routes.

Fix: added an unsafe-method origin/referer guard for authenticated API cookie requests.

## Moderate Findings

### M-01: No Scan Rate Limiting or Concurrency Controls Exist Yet

Status: fixed for the MVP scanner.

Milestone 4 adds configurable per-user and per-organization scan rate limits, prevents more than one
active scan per website and bounds scanner concurrency, redirects, timeouts and response size.

### M-02: Login Rate Limiter Was In-Memory and Unbounded

Status: fixed for MVP constraints.

The login limiter was intentionally simple but had no cap on tracked keys.

Fix: added a configurable maximum tracked key count and pruning.

### M-03: Screenshot/File Evidence Access Control Is Not Implemented

Status: fixed for screenshot evidence.

Milestone 5 stores screenshots under generated UUID filenames and serves them only through
authenticated, organization-scoped `scan_id` lookups. The endpoint never accepts a user-supplied
file path and rejects path traversal if metadata is corrupted.

### M-04: Incident Workflow and Audit Chain Are Not Implemented

Status: fixed for the MVP.

Fix: added organization-scoped incident APIs, status transition checks, note creation, viewer
read-only behavior, automatic incident creation from comparison risk and a per-organization
hash-chained `audit_logs` table with `/api/audit/verify`.

### M-05: Prompt-Injection Defences Are Not Implemented

Status: fixed in code with BYOK provider configuration.

Milestone 8 adds encrypted organization-scoped AI configuration, real provider clients, bounded
structured evidence, explicit prompt-injection protections and Pydantic response validation. The UI
states when AI is unconfigured or disabled, and deterministic remediation remains available.

### M-07: AI API Key Exposure Risk

Status: fixed in code.

AI provider keys must not be returned to the browser or stored in plaintext.

Fix: added Fernet encryption derived from `APP_SECRET_KEY`, last-four-only UI/API display, no key
storage on `AIAnalysis`, and tests proving GET responses and audit records do not include plaintext
or encrypted keys.

### M-06: Registration Allows Private/Internal URLs

Status: documented.

Website registration currently accepts syntactically valid private/internal hosts because no
outbound request is made at registration time. The scanner-grade `url_safety` module blocks these
targets and must be called immediately before any HTTP or browser navigation.

## Low Findings

### L-01: Docker Build Could Not Be Verified In This Environment

Status: unresolved environment limitation, updated.

The `docker` CLI is now installed, but the current user/session cannot access
`/var/run/docker.sock`, and passwordless sudo is unavailable. `docker compose config` passes, but
`docker compose build`, `up`, `ps`, logs and the real Docker-network demo scan remain blocked by
host daemon permissions.

### L-02: README Intro Could Be Read As Product-Complete

Status: fixed.

The README now frames SentinelSight AI as a milestone-built MVP and explicitly states which systems
are not implemented.

### L-03: No Raw Scanned Website Rendering Was Found

Status: pass.

The scan output UI renders scanned page metadata and findings through normal React text rendering.
The frontend still does not use `dangerouslySetInnerHTML`, direct `innerHTML`, `localStorage` or
`sessionStorage`.

### L-04: Implemented IDOR Checks Passed Review

Status: pass for current endpoints.

User, website asset, scan, finding, baseline, screenshot, difference image, incident and audit
records are filtered by `organization_id`; cross-organization direct object lookups return 404 in
tests.

## Verification Summary

Pre-fix checks:

- `make backend-test` passed, 17 tests.
- `npm run typecheck` passed.
- `npm run build` passed.
- Historical pre-Docker check: Docker CLI was not installed at that point in the build.

Post-security-audit checks:

- `make backend-test` passed, 35 tests.
- `make backend-lint` passed.
- `npm run typecheck` passed.
- `npm run build` passed.
- `npm audit --omit=dev` passed, 0 vulnerabilities.
- Historical pre-Docker check: Docker build was deferred until Docker became available.
- Demo-flow attempt:
  - login succeeded,
  - website registration succeeded,
  - baseline scan attempt failed with HTTP 405 because scan endpoints were not implemented yet.

Milestone 4/5 follow-up checks:

- `make backend-format` passed.
- `make backend-lint` passed.
- `make backend-test` passed, 51 tests.
- `npm run typecheck` passed.
- `npm run build` passed.
- `npm audit --omit=dev` passed, 0 vulnerabilities after network approval.
- Alembic upgrade through `202607160003` passed on SQLite.
- `docker compose config` passed.
- Docker build/runtime and real Docker-network demo scan are blocked by Docker daemon permissions.

Milestone 6/7/7B follow-up checks:

- `make backend-format` passed.
- `make backend-lint` passed.
- `make backend-test` passed, 67 tests.
- `npm run typecheck` passed.
- `npm run build` passed.
- `npm audit --omit=dev` passed, 0 vulnerabilities after network approval.
- `DATABASE_URL=sqlite:////tmp/sentinelsight_m67_audit.db ../.venv/bin/alembic upgrade head`
  passed.
- `docker compose config` passed.
- `docker compose build`, `docker compose ps`, app logs and demo-target logs were blocked by host
  Docker daemon permissions: the current user cannot access `/var/run/docker.sock`, and
  passwordless sudo is unavailable.

Milestone 8 follow-up checks:

- `make backend-format` passed.
- `make backend-lint` passed.
- `make backend-test` passed, 84 tests.
- `npm run typecheck` passed.
- `npm run build` passed.
- `npm audit --omit=dev` passed, 0 vulnerabilities after network approval.
- Alembic fresh SQLite upgrade passed through `202607160005`.
- `docker compose config` passed.
- `docker compose build` remains blocked by host Docker daemon permissions, and passwordless sudo is
  unavailable.
- Real provider connection test was not run because no user-supplied API key was available in this
  session.
