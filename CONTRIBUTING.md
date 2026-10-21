# Contributing

Thank you for contributing. Please open an issue before proposing a major architectural change.

1. Fork the repository, create a focused branch, and install with `pip install -e '.[dev]'`.
2. Add a deterministic test and a **synthetic** fixture for every new rule.
3. Run `pytest -q` and `ruff check .`.
4. Open a PR describing observed behavior, evidence and limitations.

Do **not** commit HAR traces from clients, secrets, personal data, internal URLs, or code copied from private repositories. Avoid unverified “AI root cause” assertions: diagnostics should describe evidence and distinguish hypotheses from proven facts.

All contributions are submitted under the project's MIT license.
