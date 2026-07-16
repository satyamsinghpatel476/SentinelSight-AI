# Known Limitations

- Authentication, RBAC, website asset registration, passive scanning, screenshot capture and
  baseline approval are implemented; incidents and AI remediation are not complete yet.
- The complete PS-005 baseline-to-defacement-to-incident demo flow does not pass yet because the
  visual diff, risk engine, incident workflow and tamper-evident audit chain are not implemented.
- Scanner-grade URL safety is integrated into HTTP fetching and Playwright screenshot requests.
- Docker CLI is installed, but build/runtime validation could not be completed in this session
  because the current user cannot access `/var/run/docker.sock` and passwordless sudo is unavailable.
- No invasive penetration testing, port scanning, brute forcing or exploitation will be implemented.
- JavaScript-heavy sites may render differently during screenshot comparison.
- Dynamic ads and rotating content can cause false positives.
- Screenshot comparison will be heuristic.
- AI remediation will be advisory and optional.
- Only authorized publicly reachable websites are in scope.
- The controlled `http://demo-target:9000` internal-host exception is development/test-only and must
  remain disabled in production.
- The MVP background job system and scan rate limiter are intentionally simple in-process
  mechanisms.
- Domain ownership verification may initially rely on user attestation.
