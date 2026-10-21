"""Conservative Windows-friendly local updater and dashboard supervisor.

Only fast-forward updates from the expected owner repository are permitted. No force
pull, no local-file overwrites, no shell=True, no unauthenticated updater endpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from .web import data_root

EXPECTED_REPOSITORY = "seifalla2/bugcircuit"
CHECK_INTERVAL_SECONDS = 300
WAIT_SECONDS = 2
STATUS_FILE = "updater-status.json"
REQUEST_FILE = "update-request.flag"


def runtime_dir() -> Path:
    location = data_root().parent
    location.mkdir(parents=True, exist_ok=True)
    return location


def status_path() -> Path:
    return runtime_dir() / STATUS_FILE


def request_path() -> Path:
    return runtime_dir() / REQUEST_FILE


def find_git() -> str | None:
    direct = shutil.which("git")
    if direct:
        return direct
    candidates = []
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidates.append(Path(base) / "Git" / "cmd" / "git.exe")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            desktop = Path(local) / "GitHubDesktop"
            for version in sorted(desktop.glob("app-*"), reverse=True):
                candidates += [version / "resources" / "app" / "git" / "cmd" / "git.exe",
                               version / "resources" / "app" / "git" / "bin" / "git.exe"]
    return str(next((p for p in candidates if p.is_file()), "")) or None


def trusted_remote(url: str) -> bool:
    """Require the documented GitHub owner/repo, never a substituted remote."""
    url = url.strip()
    match = re.fullmatch(r"https://(?:[^@/]+@)?github\.com/([^\s/]+/[^\s/]+?)(?:\.git)?/?", url, re.I)
    if not match:
        match = re.fullmatch(r"git@github\.com:([^\s/]+/[^\s/]+?)(?:\.git)?/?", url, re.I)
    return bool(match and match.group(1).lower() == EXPECTED_REPOSITORY)


def safe_status(**fields: object) -> None:
    """Do not record git stderr, credentials, local paths or source report data."""
    payload = {"auto_update": True, "checked_at": datetime.now(timezone.utc).isoformat(), **fields}
    destination = status_path()
    staging = destination.with_name(destination.name + ".tmp")
    staging.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    staging.replace(destination)


def current_commit(git: str | None, repo: Path) -> str:
    if not git:
        return "unknown"
    try:
        result = subprocess.run([git, "-C", str(repo), "rev-parse", "--short=8", "HEAD"],
                                capture_output=True, text=True, timeout=8, check=True)
        return result.stdout.strip()[:8] or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


class SafeUpdater:
    def __init__(self, repo: Path | None = None, git: str | None = None):
        self.repo = (repo or Path(__file__).resolve().parents[2]).resolve()
        self.git = git if git is not None else find_git()

    def run_git(self, *args: str, timeout: int = 25) -> subprocess.CompletedProcess[str]:
        if not self.git:
            raise RuntimeError("git-not-found")
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GCM_INTERACTIVE"] = "Never"
        try:
            return subprocess.run([self.git, "-C", str(self.repo), *args], env=env,
                                  capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("git-unavailable") from exc

    def checked(self, *args: str, timeout: int = 25) -> str:
        result = self.run_git(*args, timeout=timeout)
        if result.returncode:
            raise RuntimeError("git-command-failed")
        return result.stdout.strip()

    def check(self) -> tuple[str, bool]:
        """Returns status, updated. Worktrees with changes are never overwritten."""
        if not self.git:
            return "git-not-found", False
        try:
            if not trusted_remote(self.checked("remote", "get-url", "origin")):
                return "untrusted-origin", False
            if self.checked("branch", "--show-current") != "main":
                return "wrong-branch", False
            if self.checked("status", "--porcelain", "--untracked-files=no"):
                return "local-changes", False
            fetched = self.run_git("fetch", "--quiet", "origin", "main", timeout=45)
            if fetched.returncode:
                return "fetch-failed", False
            local = self.checked("rev-parse", "HEAD")
            remote = self.checked("rev-parse", "refs/remotes/origin/main")
            if local == remote:
                return "current", False
            if self.run_git("merge-base", "--is-ancestor", "HEAD", "refs/remotes/origin/main").returncode != 0:
                return "diverged", False
            changed = self.checked("diff", "--name-only", "HEAD", "refs/remotes/origin/main")
            # A single optional package refresh before starting the updated child process.
            self.checked("merge", "--ff-only", "refs/remotes/origin/main")
            if "pyproject.toml" in changed.splitlines():
                install = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."],
                                         cwd=str(self.repo), capture_output=True, text=True,
                                         timeout=150, check=False)
                if install.returncode:
                    return "dependency-install-failed", False
            return "updated", True
        except RuntimeError:
            return "git-unavailable", False
        except (OSError, subprocess.SubprocessError):
            return "git-unavailable", False


def worker_busy(port: int) -> bool:
    """Avoid cutting off a diagnostic request when a new version arrives."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", "/api/health")
        response = conn.getresponse()
        payload = json.loads(response.read())
        return response.status == 200 and bool(payload.get("busy"))
    except (OSError, ValueError, TimeoutError):
        return False
    finally:
        conn.close()


def launch_worker(repo: Path, open_browser: bool, port: int) -> subprocess.Popen:
    args = [sys.executable, "-m", "bugcircuit", "serve", "--port", str(port)]
    if open_browser:
        args.append("--open")
    return subprocess.Popen(args, cwd=str(repo))


def stop_worker(worker: subprocess.Popen | None) -> None:
    if worker is None or worker.poll() is not None:
        return
    worker.terminate()
    try:
        worker.wait(timeout=10)
    except subprocess.TimeoutExpired:
        worker.kill()
        worker.wait(timeout=4)


def supervise(interval: int = CHECK_INTERVAL_SECONDS, port: int = 8765,
              open_browser: bool = False) -> int:
    updater = SafeUpdater()
    if not (updater.repo / ".git").exists():
        safe_status(state="manual", message="git-clone-required", commit="unknown")
    elif updater.git is None:
        safe_status(state="manual", message="git-not-found", commit="unknown")
    else:
        state, _ = updater.check()
        safe_status(state=state, commit=current_commit(updater.git, updater.repo))
    worker = launch_worker(updater.repo, open_browser, port)
    print(f"BugCircuit local auto-updates check every {interval // 60} minutes.", flush=True)
    next_check = time.monotonic() + interval
    try:
        while True:
            if worker.poll() is not None:
                safe_status(state="server-stopped", commit=current_commit(updater.git, updater.repo))
                return int(worker.returncode or 1)
            requested = request_path().exists()
            if requested:
                request_path().unlink(missing_ok=True)
            if requested or time.monotonic() >= next_check:
                next_check = time.monotonic() + interval
                if worker_busy(port):
                    safe_status(state="busy", commit=current_commit(updater.git, updater.repo))
                else:
                    status, changed = updater.check()
                    safe_status(state=status, commit=current_commit(updater.git, updater.repo))
                    if changed:
                        stop_worker(worker)
                        worker = launch_worker(updater.repo, False, port)
                        if worker.poll() is not None:
                            safe_status(state="server-stopped", commit=current_commit(updater.git, updater.repo))
                            return 1
            time.sleep(WAIT_SECONDS)
    except KeyboardInterrupt:
        return 0
    finally:
        stop_worker(worker)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BugCircuit laptop server with safe GitHub updates")
    parser.add_argument("--open", action="store_true", help="Open browser on initial startup")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL_SECONDS)
    args = parser.parse_args(argv)
    if args.interval < 60 or not 1 <= args.port <= 65535:
        parser.error("Interval must be at least 60 seconds and port must be valid")
    return supervise(interval=args.interval, port=args.port, open_browser=args.open)


if __name__ == "__main__":
    raise SystemExit(main())
