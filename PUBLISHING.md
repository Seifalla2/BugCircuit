# Release and public-visibility checklist

The canonical repository is **Seifalla2/BugCircuit**. It already exists on
GitHub and must remain **private** until the owner explicitly changes its
visibility. Do not reinitialize Git or attempt to push an unrelated history.

## Before the first public release

1. Verify source code and package version against `main`.
2. Run `python -m pip install -e '.[dev,browser]'`, `pytest -q`, and `ruff check .`
   on the supported Python versions in an isolated environment.
3. Install Chromium with `python -m playwright install chromium`; run authorized
   browser/RTL smoke tests in a network sandbox. Fixture-only tests are not
   enough to establish browser compatibility.
4. Review the threat model and verify DNS-rebinding/egress safeguards.
5. Audit all repository history, issues, examples, generated HTML, and release
   artifacts for secrets, account information and client data.
6. Have at least one independent reviewer validate findings and package install.
7. Only after the above gates pass, the owner may switch visibility to Public
   in GitHub Settings and create a signed or checksum-verified release.

## Current limitations

- The v0.3 CLI, offline synthetic fixtures and wheel have been tested locally.
- GitHub Actions attempted to start in the private repository but a runner did
  not execute the job. Hosted CI is **not verified**.
- Chromium-driven browser/viewport integration is **not verified** in the
  development environment.
- No public PyPI distribution or production-hardening certification is claimed.

Use the source repository itself for future development. No new `git init`,
`git push --force`, or auto-publication is part of this process.
