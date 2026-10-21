"""Deterministic findings; confidence labels describe evidence strength, not probabilities."""

from collections import defaultdict
from urllib.parse import urljoin, urlsplit

from .models import Event, Finding, Report
from .redact import safe_url


def _finding(code: str, severity: str, confidence: str, explanation: str,
             ids: list[str], suggestions: list[str], title: str) -> Finding:
    return Finding(code, title, severity, confidence, explanation, ids[:8], suggestions)


def analyze(events: list[Event], source: str, warnings: list[str] | None = None) -> Report:
    findings: list[Finding] = []
    statuses: dict[str, list[Event]] = defaultdict(list)
    for ev in events:
        if ev.kind != "http":
            continue
        if ev.status == 401 or ev.status == 403:
            statuses["HTTP_AUTH_REJECTED"].append(ev)
        elif ev.status == 429:
            statuses["HTTP_RATE_LIMIT"].append(ev)
        elif ev.status and 500 <= ev.status <= 599:
            statuses["HTTP_SERVER_ERROR"].append(ev)
        elif ev.status == 404:
            statuses["HTTP_NOT_FOUND"].append(ev)
        if ev.status and ev.status >= 400 and any(s in urlsplit(ev.url).path.lower()
                                                   for s in ("callback", "oauth", "signin-oidc")):
            statuses["AUTH_CALLBACK_FAILED"].append(ev)

    templates = {
        "HTTP_AUTH_REJECTED": ("high", "high", "A request returned HTTP 401 or 403. The server rejected authorization, but the trace alone does not prove why.",
            ["Check authentication state and scopes on the affected request.", "Verify server session/cookie policy and API permissions."], "Authentication rejected"),
        "HTTP_RATE_LIMIT": ("medium", "high", "The server returned HTTP 429 (rate limiting).",
            ["Respect Retry-After where present.", "Introduce bounded exponential backoff and a request budget."], "Rate limit encountered"),
        "HTTP_SERVER_ERROR": ("high", "high", "One or more requests returned HTTP 5xx. The root cause requires server logs.",
            ["Match event timestamps with server logs/trace IDs.", "Inspect deploy health, upstream dependencies and timeouts."], "Server-side failure"),
        "HTTP_NOT_FOUND": ("low", "high", "One or more requested resources returned HTTP 404.",
            ["Verify route and asset paths.", "Check deployment base URL and rewrite rules."], "Missing endpoint or asset"),
        "AUTH_CALLBACK_FAILED": ("high", "medium", "An authentication-related callback path returned HTTP 4xx; the precise cause is not visible in this trace.",
            ["Compare registered redirect URI with callback URL.", "Inspect state/nonce handling and server-side validation logs."], "Authentication callback failed"),
    }
    for code, matching in statuses.items():
        severity, confidence, desc, suggestions, title = templates[code]
        findings.append(_finding(code, severity, confidence, desc, [e.id for e in matching], suggestions, title))

    for ev in events:
        msg = ev.error.lower()
        if not msg:
            continue
        if "state mismatch" in msg or "invalid state" in msg:
            findings.append(_finding("OAUTH_STATE_MISMATCH", "high", "high",
                "A runtime error explicitly reported an OAuth state mismatch.", [ev.id],
                ["Verify state persistence across the authorization redirect.", "Check cookie SameSite, domain, HTTPS and session TTL settings."],
                "OAuth state mismatch observed"))
        elif "cors" in msg and ("blocked" in msg or "policy" in msg):
            findings.append(_finding("BROWSER_CORS_BLOCK", "high", "high",
                "The browser reported a CORS policy failure; an API response alone is not enough to determine this.", [ev.id],
                ["Check Access-Control-Allow-Origin for the exact frontend origin.", "Verify preflight OPTIONS response and credentials configuration."],
                "Browser blocked a cross-origin request"))
        elif "cert_" in msg.lower() or "certificate verify failed" in msg:
            findings.append(_finding("TLS_CERT_FAILURE", "high", "high",
                "A transport error mentions TLS certificate verification.", [ev.id],
                ["Inspect certificate chain, expiry and hostname coverage.", "Do not bypass TLS verification in production."],
                "TLS certificate problem"))
        elif ev.kind in ("pageerror", "console") and (ev.kind == "pageerror" or "uncaught" in msg):
            findings.append(_finding("BROWSER_JS_ERROR", "medium", "high",
                "Browser runtime reported a JavaScript exception.", [ev.id],
                ["Use the sanitized console message and a source map to locate the error.", "Add a regression test for the failing interaction."],
                "Browser JavaScript error"))
        elif ev.kind == "span":
            findings.append(_finding("OTEL_SPAN_FAILURE", "medium", "high",
                "A traced operation was marked ERROR by instrumentation; investigate correlated server logs.",
                [ev.id], ["Use backend traces to inspect the parent span and exception details.",
                          "Check upstream dependencies and deployment versions."],
                "OpenTelemetry span error"))
        elif ev.kind == "requestfailed":
            findings.append(_finding("BROWSER_NETWORK_FAILURE", "medium", "medium",
                "Browser reported a failed network request, without a confirmed server response.", [ev.id],
                ["Check network, DNS, TLS and browser console logs.", "Compare with a direct API request to isolate client-side behavior."],
                "Browser request failed"))

    # Offline automation traces: correlation uses hashed trigger fingerprints only.
    workflows: dict[str, list[Event]] = defaultdict(list)
    trigger_groups: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for ev in events:
        if ev.kind == "layout" and "Horizontal overflow observed" in ev.error:
            findings.append(_finding("UI_HORIZONTAL_OVERFLOW", "medium", "high",
                "Rendered DOM measurements show horizontal overflow at this viewport.", [ev.id],
                ["Inspect the reported elements and fixed-width containers.",
                 "Test RTL/LTR and narrow screens before deploying changes."],
                "Horizontal layout overflow"))
        if ev.kind != "workflow":
            continue
        workflow = ev.headers.get("workflow", "unnamed")
        workflows[workflow].append(ev)
        fingerprint = ev.headers.get("trigger_fingerprint", "")
        if fingerprint and ev.method == "SUCCESS":
            trigger_groups[(workflow, fingerprint)].append(ev)
    for workflow, matches in workflows.items():
        failed = [e for e in matches if e.method in ("FAILED", "TIMEOUT")]
        timed = [e for e in matches if e.method == "TIMEOUT"]
        if failed:
            findings.append(_finding("WORKFLOW_FAILURES", "high", "high",
                f"Workflow '{workflow}' includes failed or timed-out executions.",
                [e.id for e in failed],
                ["Inspect source-system error records and retry policies.",
                 "Verify dead-letter handling and recovery without duplicate side effects."],
                "Workflow execution failures"))
        if timed:
            findings.append(_finding("WORKFLOW_TIMEOUTS", "medium", "high",
                f"Workflow '{workflow}' has explicit timeout statuses.",
                [e.id for e in timed],
                ["Check duration budgets and upstream dependencies.",
                 "Use cancellable work and bounded retries."],
                "Workflow timeouts observed"))
    for (workflow, _fingerprint), matches in trigger_groups.items():
        if len(matches) > 1:
            findings.append(_finding("DUPLICATE_TRIGGER_EXECUTIONS", "high", "medium",
                f"Workflow '{workflow}' reports multiple successful executions for one trigger fingerprint. "
                "This does not prove duplicate side effects.", [e.id for e in matches],
                ["Check idempotency keys before external writes.",
                 "Verify deduplication and at-least-once delivery handling."],
                "Possible duplicate workflow executions"))

    # Only detect a proven redirect cycle: response Location explicitly points to
    # a URL that redirects back within the same observed chain.
    redirect_links: dict[str, tuple[str, str]] = {}
    for ev in events:
        if (ev.kind == "http" and ev.status in (301, 302, 303, 307, 308)
                and ev.location and "REDACTED" not in ev.url
                and "REDACTED" not in ev.location):
            source_url = safe_url(ev.url)
            target_url = safe_url(urljoin(source_url, ev.location))
            redirect_links[source_url] = (target_url, ev.id)
    seen_cycles: set[tuple[str, ...]] = set()
    for start in redirect_links:
        visited: dict[str, int] = {}
        path: list[str] = []
        cur = start
        while cur in redirect_links and cur not in visited and len(path) <= 20:
            visited[cur] = len(path)
            path.append(cur)
            cur = redirect_links[cur][0]
        if cur in visited:
            cycle = path[visited[cur]:]
            key = tuple(sorted(cycle))
            if key not in seen_cycles:
                seen_cycles.add(key)
                findings.append(_finding("REDIRECT_CYCLE", "high", "high",
                    "Observed Location headers form a closed redirect cycle.",
                    [redirect_links[node][1] for node in cycle],
                    ["Compare authentication gates and rewrite rules for the two routes.", "Inspect cookie persistence between redirects."],
                    "Redirect cycle observed"))

    findings.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}.get(f.severity, 3), f.code))
    if not events:
        warnings = (warnings or []) + ["No diagnostic events were imported."]
    if not findings:
        warnings = (warnings or []) + ["No rules matched. This does not guarantee the application is healthy."]
    return Report(source=source, events=events, findings=findings, warnings=warnings or [])
