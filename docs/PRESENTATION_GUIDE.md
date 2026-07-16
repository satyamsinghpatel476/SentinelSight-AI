# SentinelSight AI Presentation Guide

## Demo Narrative

SentinelSight AI passively monitors an authorized website, captures a trusted baseline and then
detects a controlled defacement using deterministic evidence. The demo should emphasize that the
scan is passive, SSRF-protected and organization-scoped.

## Three-Minute Demo Sequence

Prerequisite: run this sequence from an account that can access the Docker daemon. In the current
workspace session, `docker compose config` passes but `docker compose build` and runtime checks are
blocked by `/var/run/docker.sock` permissions.

1. Start Docker Compose and open `http://127.0.0.1:8000`.
2. Log in as the Administrator demo user.
3. Open the Security Dashboard and show API/database health, website count, latest scan status,
   incident status, audit-chain verification and AI configuration status.
4. Add `http://demo-target:9000` as an authorized website.
5. Keep the demo target in normal mode and run the first scan.
6. Open the scan detail page, show the screenshot and passive findings, then approve it as the
   active baseline.
7. Switch the demo target to defaced mode with:
   ```bash
   curl -X POST \
     -H "X-Demo-Secret: $DEMO_TARGET_TOGGLE_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"mode":"defaced"}' \
     http://127.0.0.1:9000/admin/toggle
   ```
8. Run the second scan and open the comparison scan detail page.
9. Show the baseline screenshot, current screenshot, highlighted difference image, visual change
   percentage, text similarity, suspicious phrase, new script-domain finding, Deterministic Risk
   Score and score-contribution breakdown.
10. If the evaluator supplies an API key, open Settings → AI Configuration, select provider, enter
   the exact model, test the connection and save.
11. On the completed scan or incident, click Generate AI Analysis and show the exact provider/model
   stored with the result.
12. Open the generated incident, add a note, move it to Investigating, add resolution notes and
   resolve it.
13. Open Audit and show user name/email, event details and valid tamper-evident hash-chain
   verification.
14. Restore normal mode after the demo.

## Judge Talking Points

- Scans are one-page passive checks, not active exploitation.
- SSRF validation blocks localhost, private ranges, metadata services, internal hostnames and unsafe
  redirects. The Docker demo target exception is exact, development-only and rejected in production.
- Viewers cannot run scans, approve baselines or modify incidents; backend RBAC enforces this.
- Cross-organization object access returns 404.
- Raw target HTML is never rendered in the UI.
- Risk scoring is deterministic and explainable; it is not represented as AI. Informational checks,
  such as an inconclusive TLS inspection, contribute zero points unless reliable weakness evidence
  exists.
- AI Incident Analysis uses a real Bring Your Own Key provider configured by an Administrator in the
  frontend. No key is bundled in the repository.
- The exact provider and model are shown on every generated AI analysis.

## Likely Judge Questions

### Does the demo target serve malicious content?

No. The defaced mode is a controlled, test-only page with visible suspicious text and a safe
simulated external script reference. It does not execute malicious code.

### Is the audit trail blockchain?

No. It is a tamper-evident hash-chained audit trail scoped to the organization.

### What are the current limitations?

The MVP performs a single-page passive scan, screenshot comparison is heuristic, dynamic content can
cause false positives and real AI analysis requires an evaluator-supplied provider key. The current
workspace session could not complete Docker runtime verification because the user lacks Docker
socket permission.
