# BugCircuit roadmap

BugCircuit is under active development as a **local-first, evidence-led diagnostic workspace**. The items below distinguish shipped alpha capabilities from proposed work.

## Implemented in the current alpha line

- HAR import and sanitized offline findings.
- Conservative, explicitly authorized HTTP GET probes, redirect scope rules and HTTP status triage.
- Optional Playwright CLI capture; layout overflow checks at 375, 768 and 1280 px.
- Offline workflow JSON and OpenTelemetry JSON imports.
- HTML and JSON diagnostic reports with severity, confidence labels and evidence IDs.
- Single-user loopback web dashboard for import, report archive, connection to local/private cloned or public GitHub repositories and conservative Python AST heuristics.
- Optional local Ollama explanation from sanitized finding summaries.
- Synthetic-only portfolio showcase; guarded API response serialization for project paths.
- Automated Linux CI for Python 3.10, 3.12 and 3.13.

## Next — launch readiness (P0)

- Browser-based end-to-end tests on Windows (Chrome/Edge), responsive layouts and Arabic RTL flows.
- Independent assessment of DNS rebinding, request scoping, browser isolation and report redaction.
- Clean-machine installation/update/rollback tests and reproducible dependency locks.
- Review of full public Git history for sensitive data before encouraging real-world deployment.

## Next — functionality (P1)

- Bring safe, bounded Playwright collection into the local dashboard.
- Add explicit, review-before-sharing report export with clearer sanitization preview.
- Add adapter coverage for documented workflow exporters such as n8n, backed by synthetic fixtures.
- Improve finding correlation and evidence visualization without inventing root causes.

## Later — sustainable distribution (P2)

- Signed or checksum-verified desktop releases, cross-platform packaging and versioned changelog.
- Benchmarks, anonymized opt-in quality datasets and feedback from external alpha testers.
- Clear design for any future authenticated hosted offering; never expose this unauthenticated local server directly.

No planned item is a claim of implementation or security certification. See [release readiness](../PUBLISHING.md).
