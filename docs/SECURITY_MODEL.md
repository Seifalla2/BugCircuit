# Threat model and deployment guidance

## Inputs
HAR files are untrusted JSON; code is never executed during import. HAR input is capped at 25 MiB and 5,000 entries. Browser pages and live URLs may execute attacker-controlled content in Chromium or trigger network requests; restrict these to authorized targets and sandbox browser execution.

## Sensitive evidence
Raw HAR may include credentials, cookies, API keys, PII, request/response bodies, authorization data and OAuth codes. The importer discards these fields and redacts URL query values. Runtime exceptions can contain arbitrary private text; textual redaction is best-effort, not a proof of no leakage. Reports must be reviewed before uploading or sharing.

## Network egress
HTTP inspection allows only HTTP/HTTPS, disallows URL-embedded credentials, requires explicit extra redirect hosts, blocks private/reserved DNS results unless explicitly enabled, and caps redirects. Race conditions like DNS rebinding and proxy/network-level routing are beyond this validator. Run in a container with suitable network egress rules for untrusted URLs.

Playwright loads third-party assets; a single-page capture is not a comprehensive origin allowlist. Never launch an untrusted website in a privileged workspace, and do not assume Chromium sandboxing is complete.

## No mutation
No login, POST, DELETE, content-editing or auto-remediation features are provided. GET requests can still have side effects on poorly designed services, so permission remains required.

## Reporting vulnerabilities
Use the repository's private vulnerability reporting feature where available; otherwise contact repository maintainers privately. Do not publish working credentials or exploit payloads in public issues.
