# Known Limitations

- Authentication, RBAC and website asset registration are implemented; scanning, baselines,
  incidents and AI remediation are not complete yet.
- The complete PS-005 baseline-to-defacement-to-incident demo flow does not pass yet because the
  scanner, baseline, visual diff, risk engine, incident workflow and audit chain are not implemented.
- Scanner-grade URL safety helpers exist, but no outbound scanner calls them yet because scanning is
  not implemented.
- Docker build/runtime validation could not be run in this workspace because the `docker` CLI is not
  installed.
- No invasive penetration testing, port scanning, brute forcing or exploitation will be implemented.
- JavaScript-heavy sites may render differently during screenshot comparison.
- Dynamic ads and rotating content can cause false positives.
- Screenshot comparison will be heuristic.
- AI remediation will be advisory and optional.
- Only authorized publicly reachable websites are in scope.
- The MVP background job system will be intentionally simple.
- Domain ownership verification may initially rely on user attestation.
