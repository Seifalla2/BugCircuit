# Changelog

All substantial user-visible changes are documented here. BugCircuit is an alpha-stage project; the following entries distinguish released source functionality from changes on the current development line.

## Unreleased — Portfolio and repository hardening

- Introduced a responsive **synthetic-only** presentation route at `/showcase`, with OAuth, API degradation and workflow scenarios from the actual deterministic rule engine.
- Added `GET /api/showcase` with **no** user-repository, report-archive or AI-setting access and no persistent report output.
- Removed absolute local Git clone paths from normal `/api/projects` and connect-project HTTP responses; internal project storage still retains the path for authorized local audit.
- Added regression tests for showcase semantics, lack of report persistence and project-path response protection.
- Improved README, Windows guide, architecture, security policy, release checklist and portfolio demo instructions.
- Limited GitHub Actions workflows to pull requests targeting `main` and pushes to `main`, avoiding redundant branch-push runs.
- Addressed existing Ruff lint warnings while preserving deterministic analysis contracts.

## 0.5.2 alpha — Local project intelligence

- Read-only local and public GitHub clone connection in the desktop workspace.
- Bounded static inspection of **tracked** repository files; Python AST matching reduces false positives for shell/TLS/debug checks.
- Optional locally connected Ollama analysis, with adjustable loopback port; no source files sent to Ollama.
- Windows browser workspace, safe update supervisor and synthetic demos from earlier alpha iterations.

## Earlier alpha milestones

- **0.4.x:** Local loopback web dashboard and report archive.
- **0.3.x:** Offline OpenTelemetry JSON support.
- **0.2.x:** Workflow JSON analysis and optional responsive layout diagnostics.
- **0.1.x:** HAR/HTTP diagnostics, deterministic findings and HTML/JSON exports.

These are development milestones, not production certification or a claim of signed binary releases.
