# Known Limitations

- Authentication, RBAC, website asset registration, passive scanning, screenshot capture, baseline
  approval, baseline comparison, deterministic risk scoring, automatic incidents and
  tamper-evident audit-chain verification are implemented.
- Scanner-grade URL safety is integrated into HTTP fetching and Playwright screenshot requests.
- Docker Compose configuration validates, but Docker build/runtime verification could not be
  completed from this session because the current user cannot access `/var/run/docker.sock` and
  passwordless sudo is unavailable.
- Real AI provider calls require an evaluator-supplied BYOK API key configured by an Administrator
  in the frontend. No real provider test was performed in this session because no user-supplied key
  was available.
- No invasive penetration testing, port scanning, brute forcing or exploitation will be implemented.
- Scans are one-page passive checks, not recursive crawls.
- JavaScript-heavy sites may render differently during screenshot comparison.
- Dynamic ads and rotating content can cause false positives.
- Screenshot comparison is heuristic and intentionally simple for the hackathon MVP.
- AI Incident Analysis is advisory and separate from deterministic risk scoring. The application
  does not fabricate AI output.
- Only authorized websites are in scope.
- The controlled `http://demo-target:9000` internal-host exception is development/test-only and must
  remain disabled in production.
- The MVP background job system and scan rate limiter are intentionally simple in-process
  mechanisms.
- Domain ownership verification may initially rely on user attestation.
