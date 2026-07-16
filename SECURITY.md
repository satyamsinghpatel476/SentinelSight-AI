# Security Model

SentinelSight AI is designed for authorized, passive website monitoring. The project will enforce authentication, role-based authorization, organization isolation, SSRF protection, safe scanning limits and a tamper-evident audit trail as the implementation milestones progress.

## Current Milestone

Milestone 2 includes application security headers, environment-based configuration, no checked-in
secrets, health endpoints without sensitive details, Argon2 password hashing, HttpOnly cookie
authentication, basic login rate limiting, backend-enforced role checks and organization-scoped user
management.

## URL Registration Controls

- Website registration accepts only `http` and `https` URLs.
- URLs with embedded usernames or passwords are rejected.
- URL fragments are removed before storage.
- Administrators must confirm ownership or authorization before a website asset can be registered.
- Scanner-level DNS resolution, redirect validation and private-IP SSRF blocking are not enabled
  yet because outbound scanning is not implemented until the next milestone.

## Authentication Controls

- Passwords are stored as Argon2 hashes.
- Access tokens are signed JWTs stored in an HttpOnly cookie.
- Production deployments should set `COOKIE_SECURE=true`.
- Viewers and Security Analysts cannot use Administrator-only user-management APIs.
- Records owned by another organization are hidden with 404 where appropriate.

## Ethical Use

Users may scan only public websites they own or are explicitly authorized to monitor. Active exploitation, brute force attacks, directory brute forcing, port scanning and credential guessing are out of scope.

## Responsible Disclosure

Report security issues privately to the project maintainers. Include reproduction steps, affected versions and expected impact where possible.

## Known Assumptions

- `.env` files are local only and must not be committed.
- Production deployments must provide a strong `APP_SECRET_KEY`.
- Scanner protections will be implemented before website scanning is enabled.
