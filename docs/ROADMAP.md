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

## v0.3 — Offline tracing support (implemented; integration validation pending)
- OTLP JSON importer with allowlisted HTTP fields and span error evidence

## v0.4 — Candidate scope (not shipped)
- Import adapters for n8n/webhook exports
- Broader OpenTelemetry correlation and trace graph visualization
- Headless browser end-to-end CI, regression fixtures
- Signed release artifacts, repeatable dependency locks

## v1.0 — Public readiness gates (not yet satisfied)
- External beta testers and triage process
- Security and SSRF threat-model review (not merely static checks)
- Cross-platform and Chromium compatibility verification
- Benchmark datasets, public changelog and release automation

Private repository remains private until user explicitly requests publication.
Do not claim feature coverage or production readiness without tests.
