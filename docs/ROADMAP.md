# BugCircuit roadmap

## v0.1 — Complete (local tests)
- HAR importer with conservative sanitation
- API and authentication rules and bounded HTTP GET inspector
- Optional Playwright event capture and JSON/HTML reports

## v0.2 — Implemented; browser integration pending validation
- Offline workflow execution JSON importer
- Failure, timeout, and duplicate-trigger heuristic rules
- Read-only browser DOM overflow checks at three viewports
- Deterministic unit tests and synthetic fixtures

## v0.3 — Candidate scope (not shipped)
- Import adapters for n8n/webhook exports
- OpenTelemetry span import and correlation
- Headless browser end-to-end CI, regression fixtures
- Signed release artifacts, repeatable dependency locks

## v1.0 — Public readiness gates (not yet satisfied)
- External beta testers and triage process
- Security and SSRF threat-model review (not merely static checks)
- Cross-platform and Chromium compatibility verification
- Benchmark datasets, public changelog and release automation

Private repository remains private until user explicitly requests publication.
Do not claim feature coverage or production readiness without tests.
