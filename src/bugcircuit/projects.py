"""Explicitly authorized, read-only Git workspace registry and conservative audit.

A local clone (including a GitHub Desktop private clone) requires no credentials in
BugCircuit. Public GitHub URLs can be cloned to an isolated application folder.
No repository code, package script, Git hook, or plugin is ever executed here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
from urllib.parse import urlsplit

from .models import Event, Finding, Report

GITHUB_RE = re.compile(r"^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9_.-]{1,100})(?:\.git)?/?$", re.I)
PROJECT_ID_RE = re.compile(r"^[a-f0-9]{16}$")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", ".nuxt", "target", "vendor", "coverage", "__pycache__", ".idea", ".cache"}
NEVER_READ = re.compile(r"(^|/)(\.env(?:\..*)?|id_rsa|id_ed25519|.*\.(?:pem|key|p12|pfx|sqlite|db|log)|.*(?:secret|credential|token).*(?:\.json|\.ya?ml|\.txt))$", re.I)
CODE_SUFFIX = {".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".go", ".rs"}
MAX_PROJECTS = 40
MAX_FILES = 700
MAX_TEXT = 80_000


def _git() -> str:
    from .updater import find_git
    git = find_git()
    if not git:
        raise ValueError("Git is not installed. Install GitHub Desktop or Git for Windows.")
    return git


def _run_git(path: Path, *args: str, timeout: int = 15) -> str:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "Never"
    result = subprocess.run([_git(), "-C", str(path), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=env, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError("Git repository is unavailable or permission was denied")
    if len(result.stdout) > 4_000_000:
        raise ValueError("Git file listing exceeds the supported limit")
    return result.stdout.decode("utf-8", "replace")


def _public_url(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or len(value) > 260 or not GITHUB_RE.fullmatch(value):
        raise ValueError("Enter a GitHub URL like https://github.com/owner/repository")
    match = GITHUB_RE.fullmatch(value)
    assert match
    owner, repo = match.groups()
    if repo.lower().endswith(".git"):
        repo = repo[:-4]
    if repo in (".", "..") or not repo.strip("."):
        raise ValueError("Invalid repository name")
    return f"https://github.com/{owner}/{repo}.git", f"{owner}/{repo}"


def _valid_local(value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError("Choose the local Git repository folder from GitHub Desktop")
    root = Path(value.strip().strip('"')).expanduser().resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise ValueError("This folder is not a Git clone. Choose its top-level directory containing .git")
    return root


class ProjectStore:
    def __init__(self, data_dir: Path):
        self.root = data_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry = self.root / "projects.json"
        self.clones = self.root / "git-projects"

    def list(self) -> list[dict]:
        try:
            data = json.loads(self.registry.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [p for p in data if isinstance(p, dict) and PROJECT_ID_RE.fullmatch(str(p.get("id", "")))]
        except (OSError, ValueError):
            pass
        return []

    def _save(self, entries: list[dict]) -> None:
        tmp = self.registry.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.registry)

    def _register(self, path: Path, origin: str, owned: bool = False) -> dict:
        entries = self.list()
        for entry in entries:
            if entry.get("path") == str(path):
                return entry
        if len(entries) >= MAX_PROJECTS:
            raise ValueError("Maximum of 40 connected projects reached")
        item = {"id": secrets.token_hex(8), "name": path.name, "path": str(path),
                "origin": origin, "managed_clone": owned}
        entries.append(item)
        self._save(entries)
        return item

    def connect_folder(self, path: str) -> dict:
        root = _valid_local(path)
        return self._register(root, "local (GitHub Desktop)")

    def connect_public(self, url: str) -> dict:
        remote, label = _public_url(url)
        self.clones.mkdir(parents=True, exist_ok=True)
        location = self.clones / secrets.token_hex(8)
        env = os.environ.copy()
        env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never", "GIT_LFS_SKIP_SMUDGE": "1",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        try:
            # Explicit GitHub HTTPS URL; no extra protocol, --upload-pack, submodules or hooks.
            run = subprocess.run([_git(), "clone", "--depth", "1", "--single-branch",
                                  "--no-checkout", "--", remote, str(location)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 timeout=100, env=env, check=False)
            if run.returncode:
                raise ValueError("Clone failed. For a private repo, clone it in GitHub Desktop, then connect its local folder.")
            # Checkout is explicit; unlike executing a build, this materializes repository files.
            result = subprocess.run([_git(), "-C", str(location), "-c", "core.hooksPath=" + os.devnull,
                                     "checkout", "-f", "HEAD", "--", "."],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=100, env=env, check=False)
            if result.returncode:
                raise ValueError("Could not check out the repository")
            return self._register(location.resolve(), label, owned=True)
        except subprocess.TimeoutExpired as exc:
            raise ValueError("GitHub clone timed out") from exc
        finally:
            # Failed clones are removed; successful clones are preserved in app data.
            if location.exists() and not any(p.get("path") == str(location.resolve()) for p in self.list()):
                shutil.rmtree(location, ignore_errors=True)

    def get(self, identifier: str) -> dict:
        for p in self.list():
            if p["id"] == identifier:
                return p
        raise ValueError("Project not found")

    def forget(self, identifier: str) -> bool:
        entry = self.get(identifier)
        self._save([p for p in self.list() if p["id"] != identifier])
        # Never delete a user's local clone. Managed copies also remain, to avoid data loss.
        return True


def audit_project(entry: dict) -> Report:
    root = _valid_local(entry["path"])
    # Inspect tracked files only. Local untracked secrets and edits are never read.
    output = _run_git(root, "ls-files", "--cached", "-z")
    all_paths = [p for p in output.split("\0") if p]
    eligible: list[tuple[Path, str]] = []
    for raw in all_paths:
        pure = PurePosixPath(raw)
        if pure.is_absolute() or ".." in pure.parts or any(part in SKIP_DIRS for part in pure.parts):
            continue
        path = root.joinpath(*pure.parts)
        if not path.is_file() or path.is_symlink():
            continue
        eligible.append((path, pure.as_posix()))
    truncated = len(eligible) > MAX_FILES
    eligible = eligible[:MAX_FILES]
    tracked = set(all_paths)
    inspected = {name for _, name in eligible}
    events: list[Event] = []
    findings: list[Finding] = []

    def note(code: str, title: str, severity: str, description: str,
             files: list[str], checks: list[str]) -> None:
        ids = []
        for name in files[:6]:
            event_id = f"E{len(events) + 1:04d}"
            events.append(Event(id=event_id, kind="repository", url=name, error=code))
            ids.append(event_id)
        findings.append(Finding(code, title, severity, "medium", description,
                                ids, checks))

    exposed = [name for name in tracked if NEVER_READ.search(name) and
               (PurePosixPath(name).name.startswith(".env") or
                PurePosixPath(name).suffix.lower() in {".pem", ".key", ".p12", ".pfx"})]
    if exposed:
        note("REPO_SENSITIVE_FILES_TRACKED", "Potential credentials tracked in Git", "high",
             "Sensitive-looking filenames are tracked in Git. Contents were not read.",
             sorted(exposed), ["Review Git history for exposure and rotate credentials if needed.",
                               "Use a secret scanner and stop tracking secrets; deleting a file does not remove history."])
    if not any(name.lower().endswith(("readme.md", "readme.rst", "readme.txt")) for name in tracked):
        note("REPO_NO_README", "No README detected", "low",
             "No README file was found among tracked files.", ["README missing"],
             ["Document installation, usage, security assumptions and project scope."])
    if not any(name.startswith(("tests/", "test/", "__tests__/", "spec/")) or
               re.search(r"(^|/)(test_[^/]+\.py|[^/]+\.(test|spec)\.[jt]sx?)$", name)
               for name in tracked):
        note("REPO_TESTS_NOT_DETECTED", "No test files detected", "medium",
             "No conventional test file paths were detected. Tests may be stored elsewhere.",
             ["No conventional test paths"], ["Add regression tests for critical flows or document the test strategy."])
    if not any(name.startswith(".github/workflows/") or name in {".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"} for name in tracked):
        note("REPO_CI_NOT_DETECTED", "No CI workflow detected", "low",
             "No conventional continuous-integration configuration was found.",
             ["No known CI config"], ["Add automated checks before merges if the project needs CI."])

    patterns = [
        ("REPO_TLS_VERIFICATION_DISABLED", re.compile(r"\bverify\s*=\s*False\b"), "TLS verification disabled", "medium", "Review any request made with verify=False."),
        ("REPO_SUBPROCESS_SHELL", re.compile(r"\bshell\s*=\s*True\b"), "Shell command execution", "medium", "Verify command arguments never come from untrusted input."),
        ("REPO_DEBUG_ENABLED", re.compile(r"\bDEBUG\s*=\s*True\b"), "Debug mode enabled in source", "low", "Check whether this setting is used in production."),
    ]
    counts = {code: [] for code, *_ in patterns}
    scanned = 0
    for path, name in eligible:
        if NEVER_READ.search(name) or path.suffix.lower() not in CODE_SUFFIX:
            continue
        try:
            if path.stat().st_size > MAX_TEXT:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            scanned += 1
        except OSError:
            continue
        for code, regex, *_ in patterns:
            if regex.search(content) and len(counts[code]) < 5:
                counts[code].append(name)
    for code, _, title, severity, check in patterns:
        if counts[code]:
            note(code, title, severity,
                 "A potentially risky pattern appears in source. Static matches can be comments or tests; this is not proof of a vulnerability.",
                 counts[code], [check])
    warnings = ["Read-only static audit of tracked files. No code executed; no dependencies installed.",
                "Findings are heuristics, not confirmed exploitable vulnerabilities.",
                f"Inspected {len(eligible)} tracked files; read {scanned} bounded source files (sensitive files excluded)."]
    if truncated:
        warnings.append(f"Only the first {MAX_FILES} eligible files were considered; results are incomplete.")
    return Report(source="Repository audit: " + entry["name"], events=events,
                  findings=findings, warnings=warnings)


def choose_local_folder() -> str:
    """Native consent UI: selection occurs on the laptop, never in a website iframe."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        window = tk.Tk()
        window.withdraw()
        window.attributes("-topmost", True)
        try:
            choice = filedialog.askdirectory(parent=window, title="Choose a GitHub Desktop repository folder")
        finally:
            window.destroy()
        return choice or ""
    except Exception as exc:
        raise ValueError("Folder picker unavailable. Copy the repository folder path from Explorer instead.") from exc
