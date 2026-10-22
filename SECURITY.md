# Security policy

**BugCircuit v0.5.x is an alpha local diagnostics tool, not a vulnerability scanner, penetration-testing suite or publicly authenticated service.**

## Scope of security support

The actively developed source version is **v0.5.x alpha** on `main`. Older branches and packages do not receive guaranteed backported fixes. No service-level support response time is promised.

## Reporting a vulnerability

Please use **GitHub private vulnerability reporting** for [Seifalla2/BugCircuit](https://github.com/Seifalla2/BugCircuit/security/advisories/new) if enabled. If it is unavailable, reach the maintainer through a **private contact method on their GitHub profile**. Do not file a public issue with exploitation details, customer evidence, secrets, or authentication material.

A useful private report includes the affected version/commit, impact, prerequisites, and a safe reproduction using **synthetic data**.

## Important boundaries

- The bundled dashboard is designed for one person and binds to `127.0.0.1`. **It does not implement authentication.** Never expose the port to LAN or internet.
- Live HTTP inspection uses GET and best-effort destination checks; DNS rebinding and misconfigured proxy routes may undermine them. Treat unknown targets as unsafe unless network access is appropriately sandboxed.
- Optional Playwright loads page subresources. Use isolated networks when inspecting untrusted pages.
- Reports deliberately omit many sensitive fields but string redaction cannot guarantee anonymity. Review outputs before sharing.
- Repository analysis is **heuristic**, read-only and not comprehensive SAST. It is not a substitute for dedicated secrets scanning, code review or penetration testing.
- This repository is public and MIT licensed. Do not commit private implementation, secrets, real client traces or sensitive customer data.

Read [Threat model](docs/SECURITY_MODEL.md) and [Publication gates](PUBLISHING.md).
