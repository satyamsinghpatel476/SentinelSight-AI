# SentinelSight AI Security Audit

Date: 2026-07-16
Reviewer stance: independent application-security reviewer and hackathon judge.

## Scope Reviewed

- Implemented backend APIs: health, auth, users, website assets, scans, findings, baselines and
  screenshot evidence.
- Implemented frontend: foundation dashboard, login/logout, website list/add/detail, scan polling,
  baseline approval and scan detail.
- Demo target service.
- Docker and deployment configuration.
- Tests, README, progress and limitations documentation.

## Critical Findings

### C-01: PS-005 End-to-End Workflow Is Not Implemented

Status: unresolved product-completeness gap.

The required baseline-to-defacement-to-incident scenario does not currently work because these
major systems are not implemented yet:

- Visual/content comparison.
- Risk engine.
- Incident creation and workflow.
- Tamper-evident audit chain.
- AI remediation provider abstraction.

Impact: the project cannot yet satisfy the PS-005 demonstration acceptance criteria or the
attack-defence round. This is not a hidden bug in existing code; it is the next unfinished product
scope after Milestones 4 and 5.

Fix status: partially fixed. Milestones 4 and 5 now implement SSRF-safe passive scanning,
deterministic findings, screenshot capture and baseline approval. Visual comparison, incident
workflow, tamper-evident audit-chain verification and AI remediation remain unresolved and are
documented in `README.md`, `KNOWN_LIMITATIONS.md` and `PROGRESS.md`.

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

Status: unresolved product gap.

There are no incident APIs, no state-transition checks and no hash-chained audit records. Milestone 5
writes a normal baseline-approval audit entry, but tamper-evident auditability remains future work
and must not be claimed yet.

### M-05: Prompt-Injection Defences Are Not Implemented

Status: unresolved product gap.

No AI provider integration exists yet. Before AI is enabled, scanned page content must be treated as
untrusted, bounded, structured and never executable.

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

User, website asset, scan, finding, baseline and screenshot records are filtered by
`organization_id`; cross-organization direct object lookups return 404 in tests.

## Verification Summary

Pre-fix checks:

- `make backend-test` passed, 17 tests.
- `npm run typecheck` passed.
- `npm run build` passed.
- `docker --version` failed because Docker is not installed.

Post-security-audit checks:

- `make backend-test` passed, 35 tests.
- `make backend-lint` passed.
- `npm run typecheck` passed.
- `npm run build` passed.
- `npm audit --omit=dev` passed, 0 vulnerabilities.
- `docker build -t sentinelsight-ai:security-audit .` failed because Docker is not installed.
- Demo-flow attempt:
  - login succeeded,
  - website registration succeeded,
  - baseline scan attempt failed with HTTP 405 because scan endpoints are not implemented.

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
