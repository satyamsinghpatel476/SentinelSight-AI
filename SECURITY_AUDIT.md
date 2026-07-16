# SentinelSight AI Security Audit

Date: 2026-07-16
Reviewer stance: independent application-security reviewer and hackathon judge.

## Scope Reviewed

- Implemented backend APIs: health, auth, users, website assets.
- Implemented frontend: foundation dashboard, login/logout, website list/add/detail.
- Demo target service.
- Docker and deployment configuration.
- Tests, README, progress and limitations documentation.

## Critical Findings

### C-01: PS-005 End-to-End Workflow Is Not Implemented

Status: unresolved product-completeness gap.

The required baseline-to-defacement-to-incident scenario does not currently work because these
major systems are not implemented yet:

- SSRF-safe HTTP scanner.
- Screenshot capture.
- Baseline approval.
- Visual/content comparison.
- Risk engine.
- Findings.
- Incident creation and workflow.
- Tamper-evident audit chain.
- AI remediation provider abstraction.

Impact: the project cannot yet satisfy the PS-005 demonstration acceptance criteria or the
attack-defence round. This is not a hidden bug in existing code; it is the next unfinished product
scope starting at Milestone 4.

Fix status: not fixed in this audit pass because it requires completing multiple remaining
milestones. The gap is documented in `README.md`, `KNOWN_LIMITATIONS.md` and `PROGRESS.md`.

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

Status: fixed as a reusable safety boundary; still not integrated with a scanner because scanning
is not implemented.

Registration-time URL validation existed, but scanner-grade DNS/IP validation did not. If outbound
scanning were added without this boundary, localhost, private IPs, link-local addresses and metadata
services could be reachable.

Fix: added `backend/app/security/url_safety.py` with DNS resolution, IP classification,
metadata-host blocking, internal-hostname blocking and redirect-target validation helpers.

### H-05: Cookie-Authenticated Mutating API Requests Had No Origin Check

Status: fixed.

The app uses HttpOnly cookie authentication. SameSite=Lax is helpful but should not be the only CSRF
control for state-changing API routes.

Fix: added an unsafe-method origin/referer guard for authenticated API cookie requests.

## Moderate Findings

### M-01: No Scan Rate Limiting or Concurrency Controls Exist Yet

Status: unresolved product gap.

The scanner endpoints are not implemented, so there is currently no scan-rate attack surface. The
required scan concurrency and rate limits must be implemented before any outbound scanning endpoint
is exposed.

### M-02: Login Rate Limiter Was In-Memory and Unbounded

Status: fixed for MVP constraints.

The login limiter was intentionally simple but had no cap on tracked keys.

Fix: added a configurable maximum tracked key count and pruning.

### M-03: Screenshot/File Evidence Access Control Is Not Implemented

Status: unresolved product gap.

Screenshot storage and retrieval endpoints do not exist. Before screenshots are added, evidence
routes must enforce authentication and organization ownership.

### M-04: Incident Workflow and Audit Chain Are Not Implemented

Status: unresolved product gap.

There are no incident APIs, no state-transition checks and no hash-chained audit records. This must
be completed before claiming incident response or tamper-evident auditability.

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

Status: unresolved environment limitation.

The `docker` CLI is not installed in the workspace, so Docker build/runtime validation could not be
run here.

### L-02: README Intro Could Be Read As Product-Complete

Status: fixed.

The README now frames SentinelSight AI as a milestone-built MVP and explicitly states which systems
are not implemented.

### L-03: No Raw Scanned Website Rendering Was Found

Status: pass.

There is no scanner output UI yet, and the current frontend does not use `dangerouslySetInnerHTML`,
`innerHTML`, `localStorage` or `sessionStorage`.

### L-04: Implemented IDOR Checks Passed Review

Status: pass for current endpoints.

User and website asset records are filtered by `organization_id`; cross-organization direct object
lookups return 404 in tests.

## Verification Summary

Pre-fix checks:

- `make backend-test` passed, 17 tests.
- `npm run typecheck` passed.
- `npm run build` passed.
- `docker --version` failed because Docker is not installed.

Post-fix checks:

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
