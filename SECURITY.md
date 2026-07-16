# Security Model

SentinelSight AI is designed for authorized, passive website monitoring. The project will enforce authentication, role-based authorization, organization isolation, SSRF protection, safe scanning limits and a tamper-evident audit trail as the implementation milestones progress.

## Current Milestone

Milestones 1 through 5 include application security headers, environment-based configuration, no
checked-in secrets, health endpoints without sensitive details, Argon2 password hashing, HttpOnly
cookie authentication, login rate limiting, backend-enforced role checks, organization-scoped user
and website management, passive scanning, screenshot evidence capture and baseline approval.

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

## Ethical Use

Users may scan only public websites they own or are explicitly authorized to monitor. Active exploitation, brute force attacks, directory brute forcing, port scanning and credential guessing are out of scope.

## Responsible Disclosure

Report security issues privately to the project maintainers. Include reproduction steps, affected versions and expected impact where possible.

## Known Assumptions

- `.env` files are local only and must not be committed.
- Production deployments must provide a strong `APP_SECRET_KEY`.
- Visual comparison, incident workflow and tamper-evident audit-chain verification are still future
  milestones and must not be claimed as complete.
