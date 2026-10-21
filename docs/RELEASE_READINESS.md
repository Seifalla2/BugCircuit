# BugCircuit — Historical release-readiness notes (v0.3 and v0.4)

> This document records **earlier** verification, not current v0.5.2 certification. The repository is now public. Current showcase changes and API privacy regressions require a fresh test run, manual browser QA, and review of the published Git history.

## Locally verified

- 34 automated tests passed with synthetic/mock inputs.
- Offline HAR OAuth case: `AUTH_CALLBACK_FAILED` and `OAUTH_STATE_MISMATCH`.
- Offline workflow case: failure, timeout, possible duplicate trigger.
- Offline OTLP case: HTTP 503 plus backend span error.
- HTML and JSON sample reports generated successfully.
- Python wheel produced successfully as `bugcircuit-0.3.0-py3-none-any.whl`.
- Security regression for malformed URL recursion fixed and tested.

## Not yet certified for public release

- GitHub CI matrix: runner provisioning failed before executing tests while
  the repository is private; the GitHub tests are **not** passing/verified.
- Chromium browser capture and RTL viewport integration: test execution not
  available in the local environment.
- DNS rebinding and untrusted browser navigation require external network
  isolation; code-level validation alone is insufficient.
- Real-world third-party workflow export formats, Windows/macOS Python
  compatibility and load benchmarks require external validation.
- Manual audit of all history for sensitive data is still mandatory prior to
  changing repository visibility.

This is a development alpha, not a production-certified debugging suite.
No user or client repository data was imported into examples or fixtures.

## Local dashboard v0.4 verification (2026-10-21)

- Added a dependency-free, loopback-only HTTP dashboard; checks refuse nonloopback binding.
- Added offline upload flow for HAR/Workflow/OTLP and live authorized public HTTP GET.
- The raw upload bytes remain in memory; sanitized report artifacts are persisted in the OS user data folder.
- Added Windows launcher, optional login auto-start, Arabic/English controls and report management.
- CLI analysis and reporting behavior remains available and covered by regression tests.
- API security checks cover Host and Origin, no CORS opt-in, content type, size budgets and report ID paths.
- **Not yet verified:** GUI rendering on Windows Chromium, actual Windows double-click installation,
  Windows auto-start, CI runners, and optional Playwright capture in a real browser.
- **Never expose localhost port 8765 directly to the internet:** the dashboard is not designed as an authenticated web service.
