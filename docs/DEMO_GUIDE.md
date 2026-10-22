# Presenting BugCircuit to clients and portfolio audiences

This guide is for showing the **actual working diagnostic rules** without displaying private projects or claiming unsupported functionality.

## Safe demo setup

1. Clone BugCircuit, install Python 3.10+ if necessary, and launch `Start BugCircuit.cmd` on Windows.
2. Open **http://127.0.0.1:8765/showcase** directly in a fresh browser tab.
3. Hide notifications and unrelated tabs, and **share only the showcase tab** rather than your entire screen if possible.
4. Do not navigate to `/` (the owner workspace) while screen sharing. The server is local-only and not authenticated; never expose port 8765 on a public host.
5. Use only the built-in fictional sample inputs. Do not publish customer HAR, reports, secrets or sensitive repository metadata.

## Suggested demonstration flow

| Step | Showcase interaction | What you can legitimately say |
| --- | --- | --- |
| 1 | Open the showcase homepage | "BugCircuit is my local-first developer diagnostics project. It emphasizes evidence over guesses." |
| 2 | Select **Authentication callback** | "The rule engine recognizes a failed callback and an explicitly reported state mismatch, then links findings to evidence." |
| 3 | Select **API degradation** | "These are simulated HTTP 503 and 429 observations. The tool suggests what to inspect next, without claiming it knows the server-side cause." |
| 4 | Select **Workflow interruption** | "A small sample of workflow execution statuses produces failure and timeout findings." |
| 5 | Open **Suggested verification steps** | "Evidence references and next checks make a report actionable. AI is optional, not required." |
| 6 | Explain limitations | "This is an alpha local product, not a penetration test, autonomous fixer or certified SaaS." |

## What is public, what is not?

- **Public GitHub repository:** source code, documentation, fixtures and MIT licensing.
- **Showcase page:** only hard-coded fictional events processed in memory by the actual rules engine.
- **Owner dashboard:** connects to local reports, repositories, model settings and local update state. **Do not include it in public screenshots** with real data.
- **Private code:** no secret/proprietary engine can be guaranteed hidden if it has been committed to this public repository.

## Product boundaries

BugCircuit supports imports, conservative HTTP probes and an optional browser-capture CLI. It **does not** yet provide a hosted multi-user account system, dashboard-based browser automation, complete JavaScript/PHP SAST, guaranteed data anonymization, automatic remediation or independent production security validation.

Keep the discussion anchored to observed evidence, source-backed tests and transparent limitations.
