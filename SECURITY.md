# Security Model

SentinelSight AI is designed for authorized, passive website monitoring. The project enforces
authentication, role-based authorization, organization isolation, SSRF protection, safe scanning
limits and a tamper-evident audit trail for the implemented MVP workflow.

## Current Milestone

Milestones 1 through 7B include application security headers, environment-based configuration, no
checked-in secrets, health endpoints without sensitive details, Argon2 password hashing, HttpOnly
cookie authentication, login rate limiting, backend-enforced role checks, organization-scoped user
and website management, passive scanning, screenshot evidence capture, baseline approval,
comparison scans, incident workflow, hash-chain audit verification and encrypted organization-scoped
BYOK AI configuration.

## URL Registration Controls

- Website registration accepts only `http` and `https` URLs.
- URLs with embedded usernames or passwords are rejected.
- URL fragments are removed before storage.
- Administrators must confirm ownership or authorization before a website asset can be registered.
- Scanner-level DNS resolution, redirect validation and private-IP SSRF blocking are enforced
  immediately before outbound HTTP and Playwright requests.

## Scanner Controls

- Scanner requests are passive and do not exploit vulnerabilities.
- Scan targets are validated for scheme, credentials, hostname, DNS results and unsafe IP ranges.
- Redirect destinations are revalidated before being followed.
- HTTP fetching enforces redirect count, connection/read/total timeout and response-size limits.
- Browser screenshot capture blocks `file://` and forbidden subresource URLs.
- Raw target HTML is not stored or displayed.
- Screenshot retrieval is authenticated and scoped by organization ownership of the scan.
- Difference-image retrieval is authenticated and scoped by organization ownership of the scan.
- Baseline comparisons store bounded metadata and generated evidence filenames, never raw target
  HTML or user-controlled filesystem paths.
- The controlled `http://demo-target:9000` exception is development/test-only, disabled by default
  in `.env.example`, enabled by local Compose for the demo target, limited to the exact
  `demo-target` hostname/scheme/port and rejected in production.

## Authentication Controls

- Passwords are stored as Argon2 hashes.
- Access tokens are signed JWTs stored in an HttpOnly cookie.
- Production deployments should set `COOKIE_SECURE=true`.
- Viewers and Security Analysts cannot use Administrator-only user-management APIs.
- Records owned by another organization are hidden with 404 where appropriate.
- Scan, finding, baseline and screenshot records are also scoped by `organization_id`.
- Incident, incident note, difference image and audit-log records are also scoped by
  `organization_id`.
- Viewers can read incidents but cannot run scans, approve baselines, add notes or change incident
  status.
- Only Administrators can view or change AI provider configuration.
- Administrators and Security Analysts can request AI analysis on completed organization-owned scans
  or incidents; Viewers can only view previously generated analysis.

## AI Security Controls

- Deterministic risk scoring and rule-based findings are not represented as AI.
- AI provider API keys are encrypted server-side and never returned by APIs after saving.
- API keys, encrypted API keys and authorization headers are forbidden from audit metadata.
- AI prompts send bounded structured evidence only, not raw unlimited HTML.
- Scanned website content is treated as untrusted evidence and the system prompt forbids following
  instructions found in scanned content.
- Provider output must match the structured schema before it is displayed.
- Failed or invalid provider responses are stored as safe failed states without displaying raw
  provider output.

## Ethical Use

Users may scan only public websites they own or are explicitly authorized to monitor. Active exploitation, brute force attacks, directory brute forcing, port scanning and credential guessing are out of scope.

## Responsible Disclosure

Report security issues privately to the project maintainers. Include reproduction steps, affected versions and expected impact where possible.

## Known Assumptions

- `.env` files are local only and must not be committed.
- Production deployments must provide a strong `APP_SECRET_KEY`.
- AI Incident Analysis requires an evaluator-supplied API key and exact model configured from the
  frontend. Deterministic scoring and remediation guidance do not depend on AI.
