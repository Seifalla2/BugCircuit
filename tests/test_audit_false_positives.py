"""Regression tests for evidence-only repo analysis and accurate report versions."""
import json
import subprocess
from pathlib import Path

from bugcircuit import __version__
from bugcircuit.models import Event, Report
from bugcircuit.projects import ProjectStore, audit_project
from bugcircuit.reporting import export_report


def create_repo(tmp_path: Path, source: str, tests: str = "") -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# Audit test\n", encoding="utf-8")
    (root / "engine.py").write_text(source, encoding="utf-8")
    if tests:
        (root / "tests").mkdir()
        (root / "tests" / "test_bad_examples.py").write_text(tests, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    return root


def codes(repo: Path, tmp_path: Path) -> set[str]:
    store = ProjectStore(tmp_path / "state")
    report = audit_project(store.connect_folder(str(repo)))
    return {f.code for f in report.findings}


def test_comments_docstrings_and_test_fixtures_not_reported(tmp_path):
    repo = create_repo(tmp_path, '''"""Use verify=False only for isolated tests. Never shell=True."""
import re
TLS_REGEX = re.compile(r"verify=False")
# shell=True is disallowed here
MODE = "DEBUG=True"
''', 'import requests\nrequests.get("https://example.test", verify=False)\n')
    found = codes(repo, tmp_path)
    assert "REPO_TLS_VERIFICATION_DISABLED" not in found
    assert "REPO_SUBPROCESS_SHELL" not in found
    assert "REPO_DEBUG_ENABLED" not in found


def test_real_python_calls_still_reported(tmp_path):
    repo = create_repo(tmp_path, '''import requests
import subprocess
DEBUG = True
requests.get("https://example.test", verify=False)
subprocess.run("echo safe", shell=True)
''')
    found = codes(repo, tmp_path)
    assert {"REPO_TLS_VERIFICATION_DISABLED", "REPO_SUBPROCESS_SHELL", "REPO_DEBUG_ENABLED"} <= found


def test_html_uses_version_of_report(tmp_path):
    report = Report(source="test", events=[Event("E0001", "http")], findings=[])
    assert report.tool_version == __version__
    report.tool_version = "8.7.6"
    _, page = export_report(report, tmp_path)
    html = page.read_text(encoding="utf-8")
    assert "BugCircuit v8.7.6" in html
    assert "BugCircuit v0.4 ·" not in html
