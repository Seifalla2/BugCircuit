# BugCircuit — publishing and release checklist

BugCircuit is **already a public MIT-licensed GitHub repository**. Publishing commits to `main` makes those source changes visible, including the Python analysis engine. UI hiding and deleting files do not erase prior Git history or revoke existing MIT licenses.

## Current distribution status

- **Source distribution:** public repository with a local Windows launcher and Python CLI.
- **Version:** v0.5.2 alpha (source).
- **CI:** GitHub Actions Python 3.10, 3.12 and 3.13 tests and Ruff lint have been verified for the portfolio-showcase PR head; check the latest `main` run after merging.
- **Public web app:** **none**. `/showcase` runs only on the laptop's loopback server, not GitHub Pages or a hosted backend.
- **Windows executable / PyPI / signed release:** not published or independently certified.

## Release gates

- [x] Show a synthetic-only portfolio route based on deterministic rules.
- [x] Keep project filesystem paths out of ordinary project API responses.
- [x] Regression tests for synthetic samples, no saved-report side effects and project path serialization.
- [x] Automated Python matrix and Ruff lint for the feature PR.
- [ ] Complete **manual** Windows Chrome/Edge rendering, responsive, Arabic/RTL and auto-update testing.
- [ ] Independently review code and Git **history**, issues, examples, releases and artifacts for sensitive data.
- [ ] Validate SSRF/DNS rebinding and untrusted-browser boundaries in an isolated network.
- [ ] Test installation, update/rollback and wheel build in clean Windows/macOS/Linux environments.
- [ ] Add external beta feedback and provide checksum/signed distribution artifacts.

**Do not claim all security or shipping gates have passed.** A successful unit-test matrix is not production certification.

## Portfolio demo rules

Use `http://127.0.0.1:8765/showcase` on the development laptop; keep the owner workspace hidden. Only the three synthetic examples are suitable for public capture without client clearance. See [Demo guide](docs/DEMO_GUIDE.md).

## If a proprietary engine is needed later

Create a distinct **private** repository or separately hosted service for new proprietary implementation. Define the boundary explicitly, perform license review, remove secrets from *all accessible history* if any exist, and never claim existing publicly released MIT code is secret. Do not force-push or rewrite history without a reviewed remediation plan.
