# SentinelSight AI Progress

## Current Status

Milestones 1 through 8 are complete in code. A security audit hardening pass has also been
completed. The next incomplete milestone is final Docker runtime verification, a real provider AI
test with a user-supplied key and the full controlled normal-to-defaced demonstration from the
browser.

Environment note: Docker CLI is installed. Docker build/runtime verification is being rerun after
the Milestone 6/7/7B implementation. `docker compose config` passes, but build/runtime access is
blocked for this user by `/var/run/docker.sock` permissions and passwordless sudo is unavailable.

## Milestone Log

### Milestone 1 - Project Foundation

- Status: complete on 2026-07-16.
- Directory inspection: project root was empty except for `.git`, `.agents` and `.codex`.
- Created backend foundation with FastAPI, typed settings, SQLAlchemy engine/session setup,
  Alembic scaffolding, security headers, static frontend serving hooks and health/readiness routes.
- Created frontend foundation with React, TypeScript, Vite, React Router, reusable CSS and a
  health-status dashboard shell.
- Created Docker setup with a production `Dockerfile`, `docker-compose.yml`, PostgreSQL service,
  app service and demo-target service.
- Created controlled demo-target service with normal/defaced modes and a protected toggle endpoint.
- Created project documentation scaffolding: `README.md`, `SECURITY.md`, `KNOWN_LIMITATIONS.md`,
  `ARCHITECTURE.md` and `docs/PRESENTATION_GUIDE.md`.
- Created `.env.example`, `.gitignore`, `.dockerignore`, `Makefile` and required package folders.

## Verification Notes

Milestone 1 verification commands run:

- `python3 -m venv .venv` - passed.
- `.venv/bin/pip install -r backend/requirements.txt` - passed after network approval and an
  `anyio==4.7.0` compatibility pin.
- `npm install` in `frontend/` - passed with Node 18-compatible package pins.
- `npm audit --omit=dev` in `frontend/` - passed, 0 vulnerabilities.
- `.venv/bin/black backend/app backend/tests demo-target/app` - passed.
- `.venv/bin/ruff check --config backend/pyproject.toml backend/app backend/tests demo-target/app`
  - passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/pytest` from `backend/` - passed, 2 tests.
- `npm run typecheck` from `frontend/` - passed.
- `npm run build` from `frontend/` - passed.
- `make backend-test` - passed.
- `make backend-lint` - passed.
- `make frontend-build` - passed.
- Backend boot check with Uvicorn on `127.0.0.1:8010` - passed:
  - `GET /api/health` returned 200.
  - `GET /api/ready` returned 200.
- Frontend dev-server boot check on `127.0.0.1:5174` - passed with HTTP 200.
- Demo target boot check on `127.0.0.1:9001` - passed:
  - `GET /mode` returned `{"mode": "normal"}`.
  - `GET /` returned 200.
- Historical Milestone 1 note: Docker verification was deferred at that time. Docker CLI is now
  installed and later milestone verification uses Docker Compose directly.

Note: pytest plugin autoload is disabled for project tests because this environment attempts to
auto-load an unrelated global ROS pytest plugin with missing dependencies.

### Milestone 2 - Authentication and RBAC

- Status: complete on 2026-07-16.
- Pre-implementation checks:
  - `make backend-test` - passed, 2 tests.
  - `npm run typecheck` from `frontend/` - passed.
  - `npm run build` from `frontend/` - passed.
- Confirmed completed Milestone 1 features remain intact before adding auth/RBAC.
- Added `Organization` and `User` SQLAlchemy models with UUID string identifiers,
  timezone-aware timestamps, roles and active/inactive status.
- Added Alembic migration `202607160001_initial_auth_models.py`.
- Added Argon2 password hashing.
- Added JWT access tokens stored in the `sentinelsight_access` HttpOnly cookie.
- Added SameSite and production `Secure` cookie configuration support.
- Added basic in-memory login rate limiting.
- Added backend-enforced role dependencies for Administrator-only user management.
- Added organization-scoped user-management APIs that return 404 for another organization's users.
- Added `/api/auth/login`, `/api/auth/logout`, `/api/auth/me` and `/api/users` endpoints.
- Added safe demo-user seed script that reads credentials from environment variables and refuses
  placeholder passwords.
- Added frontend login page, auth context, logout action and current-user display.
- Added backend tests for:
  - valid login,
  - invalid login,
  - inactive user login rejection,
  - logout,
  - protected endpoint without authentication,
  - Administrator user management,
  - Analyst and Viewer user-management restrictions,
  - organization isolation for user records.
- Verification after implementation:
  - `make backend-format` - passed.
  - `make backend-lint` - passed.
  - `make backend-test` - passed, 11 tests.
  - `npm run typecheck` from `frontend/` - passed.
  - `npm run build` from `frontend/` - passed.
  - `npm audit --omit=dev` from `frontend/` - passed, 0 vulnerabilities.
  - `DATABASE_URL=sqlite:////tmp/sentinelsight_m2_alembic_final.db ../.venv/bin/alembic upgrade head`
    from `backend/` - passed.
  - Demo seed script against `/tmp/sentinelsight_m2_seed_final.db` - passed, created admin,
    analyst and viewer users from environment-provided credentials.
  - Local Uvicorn HTTP auth check on `127.0.0.1:8012` - passed:
    - `POST /api/auth/login` returned Administrator user data and set the auth cookie.
    - `GET /api/auth/me` returned the logged-in user via that cookie.
  - `git diff --check` - passed.

### Milestone 3 - Website Asset Management

- Status: complete on 2026-07-16.
- Added `WebsiteAsset` SQLAlchemy model with organization ownership, normalized URL, authorization
  attestation, monitoring status, risk category, contact email and creator.
- Added Alembic migration `202607160002_website_assets.py`.
- Added registration-time URL normalization:
  - only `http` and `https` are accepted,
  - embedded credentials are rejected,
  - malformed URLs are rejected,
  - default ports are normalized,
  - fragments are stripped before storage.
- Added organization-scoped website endpoints:
  - `GET /api/websites`,
  - `POST /api/websites`,
  - `GET /api/websites/{website_id}`,
  - `PATCH /api/websites/{website_id}`,
  - `DELETE /api/websites/{website_id}`.
- Added backend RBAC:
  - all authenticated roles can view organization website assets,
  - only Administrators can add, update or deactivate website assets,
  - cross-organization website IDs return 404.
- Added frontend pages:
  - Website Assets,
  - Add Website,
  - Website Detail.
- Added mandatory frontend authorization checkbox for website registration.
- Added tests for:
  - URL normalization,
  - registration authorization attestation,
  - unsafe URL rejection,
  - admin website management,
  - analyst/viewer mutation restrictions,
  - organization isolation for website records.
- Verification after implementation:
  - `make backend-format` - passed.
  - `make backend-lint` - passed.
  - `make backend-test` - passed, 17 tests.
  - `npm run typecheck` from `frontend/` - passed.
  - `npm run build` from `frontend/` - passed.
  - `npm audit --omit=dev` from `frontend/` - passed, 0 vulnerabilities.
  - `DATABASE_URL=sqlite:////tmp/sentinelsight_m3_alembic_final.db ../.venv/bin/alembic upgrade head`
    from `backend/` - passed.
  - Local Uvicorn HTTP website check on `127.0.0.1:8013` - passed:
    - authenticated as Administrator,
    - registered an authorized website,
    - listed the organization website assets.
  - `git diff --check` - passed.

### Milestone 4 - Safe Scanning Foundation

- Status: complete on 2026-07-16.
- Added `Scan` and `Finding` database models plus Alembic migration
  `202607160003_scans_findings_baselines.py`.
- Added scan status enum values `queued`, `running`, `completed` and `failed`.
- Added scan type enum values `baseline` and `comparison`.
- Added organization-scoped scan APIs:
  - `POST /api/websites/{website_id}/scans`,
  - `GET /api/websites/{website_id}/scans`,
  - `GET /api/scans/{scan_id}`,
  - `GET /api/scans/{scan_id}/findings`.
- Added backend RBAC:
  - Administrators and Security Analysts may start scans,
  - Viewers may view results but cannot start scans.
- Added organization-scoped scan and finding queries that return 404 for another organization's
  resources.
- Prevented more than one active queued/running scan for the same website.
- Added configurable in-memory per-user and per-organization scan rate limits.
- Added background scan execution using FastAPI background tasks.
- Added scanner modules:
  - `backend/app/scanners/url_validator.py`,
  - `backend/app/scanners/http_scanner.py`,
  - `backend/app/scanners/header_analyzer.py`,
  - `backend/app/scanners/content_analyzer.py`,
  - `backend/app/scanners/tls_analyzer.py`,
  - `backend/app/scanners/scan_orchestrator.py`.
- Integrated the scanner-grade SSRF validator before HTTP and browser requests.
- Added bounded HTTP fetches with connection/read/total timeouts, redirect count limits and response
  body size limits.
- Added redirect target revalidation before following redirects.
- Added a controlled local demo-target exception:
  - default is disabled,
  - production rejects it,
  - only `http://demo-target:9000` by exact scheme/hostname/port can be allowed,
  - arbitrary private IPs and other Docker hostnames remain blocked.
- Added passive deterministic findings for HTTP/HTTPS, missing security headers, unsafe CORS,
  server version disclosure, HTTP 5xx, TLS certificate expiry and session-like cookie attributes.
- Added safe scan metadata collection:
  - requested URL,
  - final URL,
  - HTTP status,
  - response time,
  - page title,
  - bounded visible text,
  - visible-text hash,
  - HTML hash,
  - redacted/summarized response headers,
  - external script and iframe domains,
  - redirect chain,
  - scan timestamps,
  - safe failure reason.
- Raw target HTML is not stored or displayed.
- Updated Website Detail UI with role-aware Run Scan, latest scan state, polling and scan history.

### Milestone 5 - Screenshot and Baseline

- Status: complete on 2026-07-16.
- Added Playwright screenshot capture with:
  - fixed viewport from environment settings,
  - navigation timeout,
  - downloads disabled,
  - unexpected dialogs dismissed,
  - request interception,
  - forbidden subresource URLs blocked,
  - `file://` blocked,
  - generated UUID screenshot filenames,
  - screenshot perceptual hash generation.
- Updated Dockerfile to install Playwright Chromium in the runtime image.
- Added secure screenshot storage under configured evidence storage.
- Added authenticated organization-scoped screenshot endpoint:
  - `GET /api/evidence/screenshots/{scan_id}`.
- Screenshot retrieval is keyed by `scan_id`; file paths are never taken from user input.
- Added path traversal protection for screenshot filename handling.
- Stored screenshot filename, content type, dimensions and perceptual hash in the `Scan` record.
- Added `Baseline` model and baseline approval workflow:
  - completed scans can be approved by Administrator or Security Analyst,
  - previous active baselines are deactivated,
  - the selected scan becomes the active trusted baseline,
  - approving user and approval timestamp are stored,
  - an audit entry is written for baseline approval.
- Added baseline APIs:
  - `POST /api/scans/{scan_id}/approve-baseline`,
  - `GET /api/websites/{website_id}/baseline`.
- Added Scan Detail UI showing status, requested/final URL, response time, page title, screenshot,
  findings, headers summary, TLS-related finding summary and safe failure message.
- Added Website Detail baseline section with active baseline metadata, screenshot and approval action.
- Added Compose-local demo seeding support through `AUTO_SEED_DEMO_USERS=true` so the Docker demo
  can create demo users from environment values when Docker daemon access is available.

Milestone 4/5 verification commands run:

- Pre-implementation `make backend-test` - passed, 35 tests.
- Pre-implementation `npm run typecheck` from `frontend/` - passed.
- Pre-implementation `npm run build` from `frontend/` - passed.
- `make backend-format` - passed.
- `make backend-lint` - passed.
- `make backend-test` - passed, 51 tests.
- `npm run typecheck` from `frontend/` - passed.
- `npm run build` from `frontend/` - passed.
- `npm audit --omit=dev` from `frontend/` - passed, 0 vulnerabilities after network approval.
- `DATABASE_URL=sqlite:////tmp/sentinelsight_m45_alembic.db ../.venv/bin/alembic upgrade head`
  from `backend/` - passed.
- `docker compose config` with explicit local demo environment values - passed.
- `docker compose build` - blocked by host Docker socket permissions:
  `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`.
- `docker compose up -d`, `docker compose ps`, `docker compose logs --tail=100 app` and the real
  Docker-network controlled demo-target scan were not run because the Docker daemon is inaccessible
  to the current user/session.

Remaining limitations after Milestone 5 were addressed by the Milestone 6/7/7B implementation below,
except for AI provider integration and distributed production job infrastructure.

Next incomplete milestone after Milestone 5 was Milestone 6 - baseline comparison, risk scoring and
incident workflow.

### Security Audit and Hardening Pass

- Status: complete on 2026-07-16.
- Created `SECURITY_AUDIT.md` with Critical, High, Moderate and Low findings.
- Confirmed the complete PS-005 baseline-to-defacement-to-incident demo flow was not implemented yet
  at the time of the audit. Milestones 4 and 5 now provide scanning, screenshots and baseline
  approval, but visual comparison, incident workflow and tamper-evident audit chain remain
  incomplete.
- Fixed High findings that were practical within the currently implemented scope:
  - production runtime validation now rejects weak/default `APP_SECRET_KEY`,
  - production runtime validation now requires `COOKIE_SECURE=true`,
  - Docker container startup now runs `alembic upgrade head` before Uvicorn,
  - Docker Compose now requires `APP_SECRET_KEY`, `POSTGRES_PASSWORD` and
    `DEMO_TARGET_TOGGLE_SECRET`,
  - demo target toggle endpoint refuses missing or placeholder secrets,
  - added cookie-authenticated unsafe-method same-origin checks,
  - added configurable request body size limit,
  - bounded the in-memory login rate limiter key map,
  - added scanner-grade `url_safety` helper with private IP, metadata, redirect-target and
    internal-hostname protections.
- Added tests for:
  - production secret/cookie validation,
  - CSRF origin blocking,
  - login limiter pruning,
  - scanner URL safety blocking localhost, private IPs, IPv6 loopback, link-local IPs, metadata
    addresses, unsupported schemes, embedded credentials and internal hostnames,
  - safe public URL acceptance,
  - DNS rebinding to private IP rejection,
  - redirect target validation.
- Verification after hardening:
  - `make backend-test` - passed, 35 tests.
  - `make backend-lint` - passed.
  - `npm run typecheck` from `frontend/` - passed.
  - `npm run build` from `frontend/` - passed.
  - `npm audit --omit=dev` from `frontend/` - passed, 0 vulnerabilities.
- Historical note: Docker build verification in that pass could not be run because `docker` was not
  installed in the workspace then.
- Historical note after Milestones 4/5: Docker CLI was installed, but full runtime validation was
  deferred to final verification.
- Historical demo-flow status after Milestones 4/5:
  - scanning, screenshot capture and baseline approval are implemented and covered by backend tests,
  - the complete baseline-to-defacement-to-incident demonstration still cannot be claimed until
    visual comparison, incident workflow and risk escalation are implemented,
  - the real Docker-network controlled demo-target scan still needs to be rerun after Docker daemon
    permissions are fixed.

### Milestone 6 - Baseline Comparison and Defacement Detection

- Status: complete in code on 2026-07-16.
- Added comparison fields to `Scan` plus Alembic migration
  `202607160004_comparison_incidents_audit.py`.
- New successful scans automatically become comparison scans when an active approved baseline
  exists.
- Added title comparison, bounded visible-text similarity, suspicious phrase detection, external
  script-domain comparison and iframe-domain comparison.
- Added screenshot visual comparison with pHash distance, changed-pixel percentage, change-level
  classification and generated UUID difference images.
- Fixed content analysis so external script/iframe domains are captured before script/style tags are
  removed for visible-text extraction.
- Added deterministic risk engine with explainable risk breakdown and score clamping.
- Added secure authenticated organization-scoped difference-image endpoint:
  `GET /api/evidence/differences/{scan_id}`.
- Updated Scan Detail UI with baseline/current/difference screenshots, comparison metrics, risk
  score, risk level, risk breakdown, suspicious phrases and new domains.
- Updated Website Detail UI to distinguish Asset Category from Latest Scan Risk and to link related
  incidents.

### Milestone 7 - Incident Management

- Status: complete in code on 2026-07-16.
- Added `Incident` and `IncidentNote` models.
- Added automatic incident creation for high-risk scans, suspicious defacement phrases or major
  visual change plus new script domain.
- Added organization-scoped APIs:
  - `GET /api/incidents`,
  - `GET /api/incidents/{incident_id}`,
  - `PATCH /api/incidents/{incident_id}`,
  - `POST /api/incidents/{incident_id}/notes`.
- Added backend RBAC:
  - Administrators and Security Analysts can change incident status and add notes,
  - Viewers are read-only,
  - cross-organization incident IDs return 404.
- Added minimal status workflow for open, investigating, resolved and false_positive.
- Added Incidents and Incident Detail frontend pages.

### Milestone 7B - Tamper-Evident Audit Trail

- Status: complete in code on 2026-07-16.
- Added `AuditLog` model with per-organization hash chaining and defined genesis hash.
- Added audit events for successful login, website creation, scan requested/completed/failed,
  baseline approval, comparison completion, incident creation, incident status changes, incident
  resolution/false positive/reopen and incident notes.
- Added `/api/audit` and `/api/audit/verify`.
- Added Audit frontend page with verification status and hash prefixes.
- Normalized audit timestamps for stable verification across SQLite and PostgreSQL and flushed each
  audit entry as it is appended so multiple entries in one transaction chain correctly.

Milestone 6/7/7B verification commands run:

- Pre-implementation `make backend-test` - passed, 51 tests.
- Pre-implementation `npm run typecheck` from `frontend/` - passed.
- Pre-implementation `npm run build` from `frontend/` - passed.
- `make backend-format` - passed.
- `make backend-lint` - passed.
- `make backend-test` - passed, 67 tests.
- `npm run typecheck` from `frontend/` - passed.
- `npm run build` from `frontend/` - passed.
- `npm audit --omit=dev` from `frontend/` - passed, 0 vulnerabilities after network approval.
- `DATABASE_URL=sqlite:////tmp/sentinelsight_m67_audit.db ../.venv/bin/alembic upgrade head`
  from `backend/` - passed.
- `docker compose config` - passed.
- `docker compose build` - blocked by Docker daemon socket permissions:
  `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`.
- `sudo -n docker compose build` - blocked because sudo requires a password.
- `docker compose ps`, `docker compose logs --tail=150 app` and
  `docker compose logs --tail=100 demo-target` - blocked by the same Docker daemon socket
  permissions.

Remaining limitations after Milestone 7B:

- AI provider integration was still incomplete at Milestone 7B; no fake AI output was generated.
- Scans remain one-page passive checks.
- Screenshot comparison is heuristic and dynamic content may cause false positives.
- The background scanner and rate limiter are in-process MVP mechanisms.
- Full Docker runtime and browser demo validation still need to be rerun by a user with Docker
  daemon access.

Next incomplete milestone after Milestone 7B was Milestone 8 - real BYOK AI Incident Analyst.

### Milestone 8 - Required Real BYOK AI Incident Analyst

- Status: complete in code on 2026-07-16.
- Preserved deterministic scanner/risk/incident behavior and labelled it separately from AI:
  - Deterministic Risk Score,
  - Rule-Based Security Finding,
  - AI Incident Analysis.
- Added organization-scoped `AIConfiguration` model and migration
  `202607160005_ai_configuration_analysis.py`.
- Added server-side API key encryption using `cryptography` Fernet with key material derived from
  `APP_SECRET_KEY`.
- API keys are never returned by configuration APIs after saving and are not stored on AI analysis
  records.
- Added `AIAnalysis` model storing provider, exact model, prompt version, status, safe error,
  generated timestamp and structured response fields.
- Added provider abstraction under `backend/app/services/ai/`:
  - Gemini provider,
  - OpenAI provider,
  - OpenAI-compatible provider with configurable base URL.
- Added Administrator-only AI configuration APIs:
  - `GET /api/ai/config`,
  - `PUT /api/ai/config`,
  - `DELETE /api/ai/config/key`,
  - `POST /api/ai/config/test`.
- Added safe AI status endpoint:
  - `GET /api/ai/status`.
- Added AI analysis APIs:
  - `POST /api/scans/{scan_id}/ai-analysis`,
  - `GET /api/scans/{scan_id}/ai-analysis`,
  - `POST /api/incidents/{incident_id}/ai-analysis`,
  - `GET /api/incidents/{incident_id}/ai-analysis`.
- Added RBAC:
  - only Administrators can view/change AI configuration,
  - Administrators and Security Analysts can request AI analysis,
  - Viewers can only view previous analysis.
- Added prompt-injection protections:
  - sends bounded structured evidence,
  - treats website text as untrusted,
  - forbids following scanned-content instructions,
  - validates provider JSON with Pydantic,
  - stores safe failed state on invalid output without fabricating fallback text.
- Added audit events for AI configuration creation/changes/key lifecycle/test requests/test
  results and AI analysis request/completion/failure, without secret metadata.
- Added frontend Settings → AI Configuration page with:
  - enabled toggle,
  - provider dropdown,
  - password API-key input,
  - exact model input,
  - optional base URL,
  - timeout,
  - Save Configuration,
  - Test Connection,
  - Remove API Key,
  - last-four-only key status.
- Added AI Incident Analysis cards to Scan Detail and Incident Detail with cost warning, provider
  and model display, generate action, loading/error states and structured result display.

Milestone 8 verification commands run:

- `make backend-format` - passed.
- `make backend-lint` - passed.
- `make backend-test` - passed, 84 tests.
- `npm run typecheck` from `frontend/` - passed.
- `npm run build` from `frontend/` - passed.
- `npm audit --omit=dev` from `frontend/` - passed, 0 vulnerabilities after network approval.
- `DATABASE_URL=sqlite:////tmp/sentinelsight_m8_ai.db ../.venv/bin/alembic upgrade head`
  from `backend/` - passed through `202607160005`.
- `docker compose config` - passed.
- `docker compose build` - blocked by Docker daemon socket permissions:
  `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`.
- `sudo -n docker compose build` - blocked because sudo requires a password.

Remaining limitations after Milestone 8:

- A real provider connection test was not performed because no evaluator/user API key was provided
  in this session. Automated tests use mocked provider calls and do not claim real-provider success.
- Docker runtime and browser demo validation are still blocked by host Docker daemon permissions for
  the current user/session.

Next incomplete milestone: final Docker runtime verification, real user-supplied-provider AI test
and complete controlled demo-target normal-to-defaced browser demonstration.
