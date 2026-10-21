# BugCircuit v0.3.0 — Release readiness (2026-10-21)

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
