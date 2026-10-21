# ⚡ BugCircuit

**Evidence-first diagnostics for browser, API and authentication failures.**

[![Tests](https://github.com/Seifalla2/BugCircuit/actions/workflows/test.yml/badge.svg)](https://github.com/Seifalla2/BugCircuit/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)
![License](https://img.shields.io/badge/license-MIT-4c1)
![Status](https://img.shields.io/badge/status-v0.5.2%20alpha-orange)

> **Status: v0.5.2 alpha** — functioning local dashboard, CLI and report generator. Local tests pass; production browser compatibility and GitHub CI still require independent verification.

BugCircuit imports an existing HTTP Archive (HAR), probes an authorized URL with bounded HTTP GET requests, or optionally observes a single page through Playwright. A deterministic rules engine links errors to evidence IDs and produces portable HTML and JSON reports. The deterministic analysis works without an LLM. An **optional local Ollama model** can explain sanitized findings. It does not run aggressive scans, collect credentials, or apply fixes automatically.

### Portfolio showcase (synthetic data only)

Start the local dashboard, then open **[the Showcase view](http://127.0.0.1:8765/showcase)**. It is a separate, responsive presentation designed for screen-sharing and screenshots. The three example scenarios (OAuth, API failures and workflow interruption) are produced by the real deterministic rule engine from **fictional inputs**. No connected repositories, saved reports, local file paths, model settings or customer data are requested by this view. The showcase endpoint does not write a report to disk.

The private owner workspace remains at `http://127.0.0.1:8765/`. **Do not screen-share the owner workspace with connected private repositories or real client reports open.** The portfolio page is *not* a separate hosted service or an authentication boundary: anyone using the unlocked laptop can navigate to the local workspace. Never publish port 8765 to the internet.

**Source visibility:** This GitHub repository is publicly visible and MIT-licensed. All code committed here, including the Python engine, is accessible. UI hiding, JavaScript minification, and removing files from current commits cannot make already-published source private. A proprietary core would need a distinct private repository and a documented distribution/API boundary; review prior releases and license obligations before any migration.

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

## Local web dashboard on Windows (recommended)

> **No recurring PowerShell commands needed.** The repo includes a local-first
> browser dashboard, a double-click launcher and an optional Windows login starter.

1. Install **Python 3.10+** once if required.
2. Use **GitHub Desktop → Clone repository** for `Seifalla2/BugCircuit`.
3. Open the cloned folder in Explorer and double-click **`Start BugCircuit.cmd`**.
4. The first launch installs into an isolated `.venv`, then opens **http://127.0.0.1:8765/**.
   Leave the small server window running. Bookmark this address.
5. Optionally double-click **`Enable Auto-start.cmd`** once to start the app at Windows login;
   `Disable Auto-start.cmd` reverses this. No router port forwarding.
6. The Windows launcher checks for clean fast-forward updates periodically while running. If update is blocked by local edits or authentication, use GitHub Desktop **Fetch origin → Pull origin** and restart.

Dashboard features: English/Arabic, local report archive and delete, upload HAR/Workflow/OTLP
JSON, run bounded public HTTP GET diagnostics against explicitly authorized URLs, download
sanitized HTML/JSON reports, and an offline demo. Browser Playwright capture remains an
optional CLI feature and is not a dashboard capability yet. The app is **bound to
127.0.0.1 only**, not internet-accessible. See [Windows guide](README-WINDOWS.md).

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

## Connect GitHub and local repositories (v0.5.2 alpha)

The browser interface now includes **Projects**, a per-user, read-only source inspection workspace:

- **Public GitHub repositories:** paste a full `https://github.com/owner/repository` link; BugCircuit uses Git to clone with a fixed `github.com` HTTPS remote into a local managed cache. Git must be installed. This is explicitly initiated by the user; no scheduled clone/pull of third-party projects occurs.
- **Private GitHub repositories:** clone them using **GitHub Desktop**, authenticate there, and choose the clone's root folder under **Projects → Local folder**. The browser UI also has an optional native folder picker. BugCircuit does not request GitHub access tokens or repository write scopes.
- **Source audit:** checks tracked files only, skips `.env` content, passwords, symlinks, node_modules, virtual environments, large binary files and source trees beyond scan limits. Reports potential CI/test gaps, TLS verification bypass, shell execution patterns, and names of sensitive-looking tracked files. Python source-code patterns are checked with the AST (not text matching), excluding test fixtures to reduce false positives; these rules do **not** analyze JS/TS/PHP source. Findings remain **heuristics**, not proofs of vulnerabilities. It never runs code or changes user files.
- **Local AI explanation (optional):** enumerates locally installed Ollama models and produces a read-only advisory based on sanitized diagnostic findings. Ollama is accessed through `127.0.0.1` only, on port `11434` by default. If yours uses `11435` or another local port, set it via **Explain report → Ollama port → Connect Ollama**; the selection persists on your device. **No raw source code** is sent to the model, and there is no hosted-model fallback. Installing Ollama and a model is a user opt-in.

Repository findings and HTTP traces answer different questions: a site can return 403 to a machine client while the site works normally for visitors, because CDN/WAF rules can differ. v0.5 distinguishes observed 403 access denial from observed HTTP 401 authentication rejection.

**Limitations:** This is an initial static review, not a general code understanding agent, vulnerability certification, OAuth integration, unattended code fixer, or full web crawler. Public Git clones need internet connectivity and may be slow for large repos. The application stays bound to loopback; do not expose it to other devices without separate authentication and transport security. For private GitHub accounts, use the locally cloned repository method rather than sharing credentials.

[Windows onboarding and privacy guide](README-WINDOWS.md)

**After upgrading:** New scans use the corrected AST checks and report version. Existing saved reports are historical snapshots and are not rewritten automatically. Re-run **Projects → Analyze code** to verify a fixed false positive.
