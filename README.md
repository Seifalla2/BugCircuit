# ⚡ BugCircuit

**Evidence-first diagnostics for browser, API and authentication failures.**

[![Tests](https://github.com/Seifalla2/BugCircuit/actions/workflows/test.yml/badge.svg)](https://github.com/Seifalla2/BugCircuit/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)
![License](https://img.shields.io/badge/license-MIT-4c1)
![Status](https://img.shields.io/badge/status-v0.3%20alpha-orange)

> **Status: v0.3 alpha** — functioning CLI and report generator, not yet proven in real-world deployments. The GitHub CI status is unverified while hosted runners are unavailable in the private repository.

BugCircuit imports an existing HTTP Archive (HAR), probes an authorized URL with bounded HTTP GET requests, or optionally observes a single page through Playwright. A deterministic rules engine links errors to evidence IDs and produces portable HTML and JSON reports. It **does not use an LLM, run aggressive scans, collect credentials, or apply fixes automatically**.

### Why it exists

Debugging often begins with vague messages like “login failed” or “the server is down.” BugCircuit focuses on the evidence you actually have:

- **HTTP:** 401/403, 404, 429, 5xx with suggested follow-up checks.
- **OAuth-related:** callback failures and *explicitly observed* state mismatches.
- **Browser:** console errors, CORS policy blocks, request failures and JavaScript exceptions.
- **Automation:** offline workflow execution exports with failure, timeout and potential duplicate-trigger detection.
- **UI layout (optional):** browser-rendered horizontal overflow at 375, 768 and 1280 px using `capture --check-layout`.
- **Redirects:** loops proven by observed Location edges (conservatively ignores redacted query-bearing redirects).
- **Reports:** sanitized event timeline, finding severity, confidence *labels*, and suggested verification steps.

The tool distinguishes **observed symptoms** from **hypothesized root causes**. HTTP 403 is evidence that authorization was rejected; it is **not** proof that a particular OAuth scope or cookie policy caused it.

## Quick start

Python 3.10+ is required.

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .

# Fully offline demo with a synthetic, fake HAR file:
bugcircuit analyze-har examples/oauth-state-mismatch.har --out ./report

# Open ./report/report.html, or consume ./report/report.json
```

**Workflow trace example (offline, synthetic):**

```bash
bugcircuit analyze-workflow examples/workflow-failures.json --out ./workflow-report
```

`analyze-workflow` accepts a JSON object with `executions` records containing
`workflow`, `status` (`success`, `failed`, `timeout`, `running`, `cancelled`, `retried`),
optional `trigger_id`, `duration_ms`, `timestamp`, and `error`. Payloads are ignored.
Trigger IDs are hashed for duplicate detection; repeated success for the same fingerprint
is a **signal for investigation**, not proof of duplicate external side effects.

**OpenTelemetry trace example (offline, synthetic):**

```bash
bugcircuit analyze-otel examples/otel-errors.json --out ./otel-report
```

The OTLP importer accepts JSON `resourceSpans` / `scopeSpans` / `spans`,
retains only HTTP status/method/url metadata and explicit ERROR status,
and discards trace IDs, span links, arbitrary attributes and event payloads.

**Other supported commands:**

```bash
# Safe by default: one explicit public HTTP(S) target; bounded redirects
bugcircuit inspect https://example.com --out ./report

# Explicitly allow a trusted, second redirect hostname when needed
bugcircuit inspect https://example.com --allow-host login.example.com --out ./report

# Only for your own local development server; explicit private-network opt-in
bugcircuit inspect http://127.0.0.1:8000 --allow-private --out ./report

# Browser capture is optional
pip install -e '.[browser]'
python -m playwright install chromium
bugcircuit capture https://example.com --check-layout --out ./report

# CLI help
bugcircuit --help
```

You can also run `python -m bugcircuit` after installing.

### Example result

```text
BugCircuit v0.3.0 • 2 events • 2 findings
[HIGH] AUTH_CALLBACK_FAILED: Authentication callback failed
[HIGH] OAUTH_STATE_MISMATCH: OAuth state mismatch observed
JSON: .../report/report.json
HTML: .../report/report.html
```

This example is generated from a **synthetic** HAR fixture that explicitly contains an OAuth state error. A generic callback failure will **not** be labeled a state mismatch without corresponding evidence.

## Design

```text
            Authorized input
  ┌──────────────┼────────────────┐
  │              │                │
Offline HAR   HTTP GET       Playwright Page
 parser       probe          capture (optional)
  │              │                │
  └──────────────┼────────────────┘
                 ▼
        Redaction & Event Model
                 ▼
      Deterministic Rule Engine
                 ▼
      Findings + Evidence IDs
                 ▼
          JSON / HTML
```

```text
src/bugcircuit/
  cli.py         commands and input validation
  har.py         bounded, sanitized HAR import
  probe.py       scoped HTTP GET and redirect checks
  browser.py     optional Chromium event capture
  redact.py      conservative sanitization
  models.py      stable structured event schema
  analyze.py     evidence-backed findings
  reporting.py   static offline report generation
  automation.py  offline workflow execution importer
  otel.py        bounded offline OTLP JSON span importer
  layout.py      read-only rendered DOM overflow checks
examples/        synthetic fixtures only
tests/           isolated unit and integration-like CLI tests
docs/            scope, security, roadmap and architecture
```

## Safety and privacy

**Use only on systems you own or are authorized to test.** HAR imports are offline, but HAR files themselves may contain passwords or personal data. Inspect raw files before sharing; **do not upload raw HAR files to GitHub**. Generated reports omit cookies, authorization headers, request and response bodies, URL credentials, fragments and URL query values. Error messages receive best-effort text sanitization, so **review reports before public distribution**; arbitrary application-provided messages can still expose private information.

Network operations are opt-in. HTTP inspection sends GET only, limits redirect hops, blocks non-public IP ranges by default, and refuses cross-host redirects unless an extra hostname is explicitly allowed. DNS validation is **best effort, not immune to DNS rebinding**; run probes in a network-sandboxed environment for untrusted targets. Browser capture fetches subresources and may reach other origins; **never run it on untrusted pages from a privileged network**. No built-in account login or form automation is included in v0.2.

See [Security Policy](SECURITY.md) and [Threat Model](docs/SECURITY_MODEL.md).

## Confidence and limitations

- `confidence=high` means the symptom is directly observed, **not** that the root cause was verified.
- CORS cannot be proven from an HTTP response alone; requires browser-observed error text.
- OAuth callback errors provide directions for investigation; they do not reveal server-side session state.
- The tool does not instrument private backends, inspect server logs or obtain traces from inaccessible services.
- Source maps, workflow graphs, UI screenshots and automated root-cause remediation are **not** part of v0.3.
- Tests use deterministic fixtures and mocks; production browser compatibility and large-trace benchmarks remain open validation work.

## Development

```bash
pip install -e '.[dev]'
pytest -q
ruff check .
```

Run the offline synthetic cases and inspect the generated results:

```bash
bugcircuit analyze-har examples/api-failures.har --out ./report
```

See [Architecture](docs/ARCHITECTURE.md), [Roadmap](docs/ROADMAP.md), and [Contributing](CONTRIBUTING.md).

## Portfolio / client use cases

1. **OAuth callback failure:** document state-mismatch *evidence* and suggested server-side checks.
2. **API outage triage:** identify 401/429/5xx timeline and next debugging actions.
3. **Redirect regressions:** report observed redirect cycles with event references.
4. **Automation reliability:** identify explicit workflow failures and potential duplicates.
5. **Responsive diagnostics:** detect horizontal overflow in rendered DOM at three viewport widths.

All shipped fixtures use fictional `.test` domains, not client data. Future plans include optional automation integrations and Playwright screenshot artifacts after privacy controls and testing.

## License

[MIT](LICENSE). Contributions welcome. This is an independent open-source project and is not affiliated with Playwright, GitHub, or any third-party authentication service.
