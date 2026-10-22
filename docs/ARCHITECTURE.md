# Architecture and invariants

BugCircuit v0.5.x builds on independent collectors and one deterministic analysis engine:

- **HAR import**: bounded 25 MiB JSON parsing, maximum 5,000 entries, strict extraction of request URL, method, response status, duration, redirect destination, and selected nonsecret metadata.
- **HTTP probe**: bounded GET-only requests with an allowlist for each redirect hop and best-effort resolution checks against internal IPs. Never forwards tokens or sessions.
- **Browser collector**: optional Playwright Chromium collects response status, request failures, page errors and error-level console messages from one navigation. Capped at 2,000 events. Collection may include third-party origin subresources.
- **Normalization**: all collectors emit `Event` objects that contain only sanitized metadata.
- **Correlation rules**: deterministic `Finding` objects reference event IDs. High confidence describes a directly observed symptom rather than validated root cause.
- **Presentation**: local HTML/JSON reports and a browser dashboard on `127.0.0.1`, plus an optional local Ollama explanation of sanitized findings. The deterministic analysis does not require an AI provider.

## Stable structured schema

`Report.schema_version=1.0` with `source`, `generated_at`, `tool_version`, `warnings`, `events[]`, `findings[]`.

An `Event` has `id`, `kind`, `url`, `method`, `status`, `timestamp`, `duration_ms`, `location`, `error` and an allowlisted `headers` object. `Finding` has `code`, `title`, `severity`, `confidence`, `explanation`, `evidence_ids`, and `recommendations`.

## Design decisions

Rules must avoid overclaiming root causes. Redacted URL query values are not suitable as redirect-cycle identity, so those edges are excluded from cycle matching. Source/server error text is untrusted; sanitize and HTML-escape before rendering. Inputs are not allowed to change production infrastructure.

## Original non-goals (v0.1) — historical

No workflow execution engine, repository mutation, automated fixer, login replay, unrestricted crawling, active port scanning, server code analysis, secrets collection, screenshot recording or background monitoring.


## v0.2 extension

`automation.py` ingests a minimal user-supplied `executions` JSON array and drops arbitrary
payloads. `trigger_id` is hashed to 16 hexadecimal characters so repeated triggers can be
correlated without displaying input values. This is not cryptographic anonymization against
small or predictable ID spaces. `layout.py` operates only on DOM geometry; it does not
collect screenshots, page source or user-entered form values. The optional Playwright
browser can still contact multiple origins and should run inside an isolated network.

## v0.5.x local workspace and portfolio showcase

- `web.py` serves the owner dashboard, report API and a separate `/showcase` view. Both bind only to loopback; neither is a remote authenticated service.
- `/api/showcase` derives three hard-coded synthetic scenarios through the deterministic engine. It never loads personal project state or persisted reports and never writes a report.
- The `ProjectStore` registry keeps local project paths server-side. Standard project-list and connect-project API responses return display metadata only.
- `projects.py` performs a capped, tracked-files-only Python AST heuristic review. It neither executes project code nor mutates its Git working tree.
- `local_ai.py` talks only to a configured loopback Ollama port, using sanitized findings rather than source data. AI output is unverified guidance.
- `updater.py` checks for clean fast-forward updates from the expected GitHub repository and defers while analysis jobs are active.
