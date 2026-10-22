"""Offline Git integration tests: never contact GitHub or any external service."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from bugcircuit import updater


def git(directory: Path, *args: str):
    return subprocess.run(["git", "-C", str(directory), *args], text=True,
                          capture_output=True, check=True).stdout.strip()


@pytest.mark.parametrize("remote,expected", [
    ("https://github.com/Seifalla2/BugCircuit.git", True),
    ("https://github.com/Seifalla2/BugCircuit", True),
    ("git@github.com:Seifalla2/BugCircuit.git", True),
    ("https://github.com/Seifalla2/BugCircuit-external.git", False),
    ("https://evil.example/Seifalla2/BugCircuit", False),
    ("https://github.com/other/BugCircuit.git", False),
])
def test_expected_origin_validation(remote, expected):
    assert updater.trusted_remote(remote) == expected


@pytest.fixture
def repos(tmp_path, monkeypatch):
    if shutil.which("git") is None:
        pytest.skip("Git CLI unavailable")
    source, bare, laptop = (tmp_path / key for key in ("source", "remote.git", "laptop"))
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.email", "test@bugcircuit.invalid")
    git(source, "config", "user.name", "Unit Test")
    (source / "README.md").write_text("base\n")
    git(source, "add", "README.md")
    git(source, "commit", "-m", "base")
    subprocess.run(["git", "clone", "--bare", str(source), str(bare)], check=True,
                   capture_output=True)
    subprocess.run(["git", "clone", str(bare), str(laptop)], check=True,
                   capture_output=True)
    monkeypatch.setattr(updater, "trusted_remote", lambda _url: True)
    return source, bare, laptop


def test_update_to_new_clean_commit(repos):
    source, bare, laptop = repos
    git(source, "remote", "add", "origin", str(bare))
    (source / "README.md").write_text("new\n")
    git(source, "commit", "-am", "new")
    git(source, "push", "origin", "main")
    updater_instance = updater.SafeUpdater(repo=laptop, git=shutil.which("git"))
    assert updater_instance.check() == ("updated", True)
    assert (laptop / "README.md").read_text() == "new\n"
    assert updater_instance.check() == ("current", False)


def test_wont_overwrite_dirty_checkout(repos):
    _source, _bare, laptop = repos
    (laptop / "README.md").write_text("unsaved local change\n")
    update = updater.SafeUpdater(repo=laptop, git=shutil.which("git"))
    assert update.check() == ("local-changes", False)
    assert (laptop / "README.md").read_text() == "unsaved local change\n"


def test_updater_rejects_untrusted_remote(repos, monkeypatch):
    _, _, laptop = repos
    monkeypatch.setattr(updater, "trusted_remote", lambda _url: False)
    assert updater.SafeUpdater(repo=laptop, git=shutil.which("git")).check() == ("untrusted-origin", False)


def test_status_saves_no_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("BUGCIRCUIT_DATA_DIR", str(tmp_path / "BugCircuit" / "reports"))
    updater.safe_status(state="current", commit="12345678")
    payload = json.loads(updater.status_path().read_text())
    assert payload["commit"] == "12345678" and payload["auto_update"]
    assert updater.REQUEST_FILE not in updater.status_path().name
