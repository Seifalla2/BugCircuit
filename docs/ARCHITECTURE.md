# Architecture and invariants

BugCircuit v0.1 consists of independent collectors and one deterministic analysis engine:

- **HAR import**: bounded 25 MiB JSON parsing, maximum 5,000 entries, strict extraction of request URL, method, response status, duration, redirect destination, and selected nonsecret metadata.
- **HTTP probe**: bounded GET-only requests with an allowlist for each redirect hop and best-effort resolution checks against internal IPs. Never forwards tokens or sessions.
- **Browser collector**: optional Playwright Chromium collects response status, request failures, page errors and error-level console messages from one navigation. Capped at 2,000 events. Collection may include third-party origin subresources.
- **Normalization**: all collectors emit `Event` objects that contain only sanitized metadata.
- **Correlation rules**: deterministic `Finding` objects reference event IDs. High confidence describes a directly observed symptom rather than validated root cause.
- **Presentation**: local-only `report.json` plus HTML report, no calls to AI APIs or cloud services.

## Stable structured schema

`Report.schema_version=1.0` with `source`, `generated_at`, `tool_version`, `warnings`, `events[]`, `findings[]`.

An `Event` has `id`, `kind`, `url`, `method`, `status`, `timestamp`, `duration_ms`, `location`, `error` and an allowlisted `headers` object. `Finding` has `code`, `title`, `severity`, `confidence`, `explanation`, `evidence_ids`, and `recommendations`.

## Design decisions

Rules must avoid overclaiming root causes. Redacted URL query values are not suitable as redirect-cycle identity, so those edges are excluded from cycle matching. Source/server error text is untrusted; sanitize and HTML-escape before rendering. Inputs are not allowed to change production infrastructure.

## Non-goals in v0.1

No workflow execution engine, repository mutation, automated fixer, login replay, unrestricted crawling, active port scanning, server code analysis, secrets collection, screenshot recording or background monitoring.


## v0.2 extension

`automation.py` ingests a minimal user-supplied `executions` JSON array and drops arbitrary
payloads. `trigger_id` is hashed to 16 hexadecimal characters so repeated triggers can be
correlated without displaying input values. This is not cryptographic anonymization against
small or predictable ID spaces. `layout.py` operates only on DOM geometry; it does not
collect screenshots, page source or user-entered form values. The optional Playwright
browser can still contact multiple origins and should run inside an isolated network.
