"""Loopback-only, dependency-free web UI for BugCircuit's existing diagnostic engines.

Local requests and reports never leave the machine unless the user explicitly runs an
HTTP probe against an authorized target. Imported source payloads stay in memory.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__
from .analyze import analyze
from .automation import parse_workflow
from .har import MAX_HAR_BYTES, parse_har
from .models import Event
from .otel import parse_otlp
from .probe import ScopeError, inspect_url
from .reporting import export_report
from .projects import ProjectStore, audit_project, choose_local_folder
from .local_ai import models as ollama_models, explain as explain_with_ollama, pull_model, INSTALLABLE_MODELS

MAX_REQUEST_BYTES = MAX_HAR_BYTES + 2048  # The JSON envelope adds a small overhead.
REPORT_ID = re.compile(r"^[a-f0-9]{16}$")
STATIC = Path(__file__).with_name("static")


def data_root() -> Path:
    """Store reports outside GitHub clones / OneDrive folders."""
    custom = os.environ.get("BUGCIRCUIT_DATA_DIR", "").strip()
    if custom:
        return Path(custom).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BugCircuit" / "reports"
    return Path.home() / ".local" / "share" / "bugcircuit" / "reports"


def summary(data: dict, report_id: str) -> dict:
    findings = data.get("findings", [])
    return {
        "id": report_id,
        "source": data.get("source", "Unknown"),
        "generated_at": data.get("generated_at", ""),
        "events": len(data.get("events", [])),
        "findings": len(findings),
        "high": sum(f.get("severity") == "high" for f in findings),
        "top_findings": [{"code": f.get("code"), "title": f.get("title"),
                          "severity": f.get("severity"), "confidence": f.get("confidence")}
                         for f in findings[:5]],
    }


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], directory: Path | None = None):
        if address[0] != "127.0.0.1":
            raise ValueError("BugCircuit web UI binds only to 127.0.0.1")
        self.reports_dir = (directory or data_root()).resolve()
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.projects = ProjectStore(self.reports_dir.parent)
        self.model_install = {"state": "idle", "model": None, "phase": "", "downloaded": 0, "total": 0}
        self.model_install_lock = threading.Lock()
        self.active_jobs = 0
        self.jobs_lock = threading.Lock()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: LocalServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        # Avoid leaking target URLs and report paths to the terminal.
        return

    def _headers(self, status: HTTPStatus, ctype: str, count: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(count))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'")
        self.end_headers()

    def _send(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
        self._headers(status, ctype, len(body))
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: object) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json(status, {"error": message})

    def _trusted_request(self, modifying: bool = False) -> bool:
        port = self.server.server_port
        allowed_hosts = {f"localhost:{port}", f"127.0.0.1:{port}"}
        if self.headers.get("Host", "").lower() not in allowed_hosts:
            self._error(HTTPStatus.FORBIDDEN, "Use the local BugCircuit URL")
            return False
        if modifying:
            origin = self.headers.get("Origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme != "http" or parsed.netloc.lower() not in allowed_hosts:
                    self._error(HTTPStatus.FORBIDDEN, "Cross-origin request rejected")
                    return False
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "JSON requests required")
                return False
        return True

    def _report_path(self, report_id: str) -> Path | None:
        if not REPORT_ID.fullmatch(report_id):
            return None
        return self.server.reports_dir / report_id

    def _list_reports(self) -> list[dict]:
        results = []
        for folder in self.server.reports_dir.iterdir():
            if not folder.is_dir() or not REPORT_ID.fullmatch(folder.name):
                continue
            file = folder / "report.json"
            if not file.is_file():
                continue
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                results.append(summary(data, folder.name))
            except (OSError, ValueError, TypeError, AttributeError):
                continue
        return sorted(results, key=lambda x: (x["generated_at"], x["id"]), reverse=True)[:100]

    def do_GET(self) -> None:
        if not self._trusted_request():
            return
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            return self._static("index.html", "text/html; charset=utf-8")
        resources = {"/assets/styles.css": ("styles.css", "text/css; charset=utf-8"),
                     "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
                     "/favicon.svg": ("favicon.svg", "image/svg+xml")}
        if path in resources:
            name, ctype = resources[path]
            return self._static(name, ctype)
        if path == "/api/health":
            return self._json(HTTPStatus.OK, {"ok": True, "version": __version__,
                                               "mode": "loopback", "host": "127.0.0.1",
                                               "busy": self.server.active_jobs > 0})
        if path == "/api/update-status":
            from .updater import status_path
            try:
                result = json.loads(status_path().read_text(encoding="utf-8"))
                if not isinstance(result, dict):
                    raise ValueError("Invalid status")
            except (OSError, ValueError):
                result = {"auto_update": False, "state": "not-running", "commit": "unknown"}
            return self._json(HTTPStatus.OK, result)
        if path == "/api/projects":
            return self._json(HTTPStatus.OK, {"projects": self.server.projects.list()})
        if path == "/api/ai/download-status":
            with self.server.model_install_lock:
                status = dict(self.server.model_install)
            return self._json(HTTPStatus.OK, status)
        if path == "/api/ai/models":
            return self._json(HTTPStatus.OK, {"models": ollama_models(), "provider": "ollama-local"})
        if path == "/api/reports":
            reports = self._list_reports()
            return self._json(HTTPStatus.OK, {"reports": reports, "total": len(reports)})
        match = re.fullmatch(r"/api/reports/([a-f0-9]{16})", path)
        if match:
            folder = self._report_path(match.group(1))
            file = folder / "report.json" if folder else None
            if file and file.is_file():
                return self._send(HTTPStatus.OK, file.read_bytes(), "application/json; charset=utf-8")
        match = re.fullmatch(r"/reports/([a-f0-9]{16})\.(html|json)", path)
        if match:
            folder = self._report_path(match.group(1))
            file = folder / ("report." + match.group(2)) if folder else None
            if file and file.is_file():
                kind = "text/html" if match.group(2) == "html" else "application/json"
                return self._send(HTTPStatus.OK, file.read_bytes(), kind + "; charset=utf-8")
        self._error(HTTPStatus.NOT_FOUND, "Not found")

    def _static(self, name: str, ctype: str) -> None:
        try:
            return self._send(HTTPStatus.OK, (STATIC / name).read_bytes(), ctype)
        except FileNotFoundError:
            return self._error(HTTPStatus.NOT_FOUND, "Static asset missing")

    def do_POST(self) -> None:
        if not self._trusted_request(modifying=True):
            return
        project_audit = re.fullmatch(r"/api/projects/([a-f0-9]{16})/audit", self.path)
        report_ai = re.fullmatch(r"/api/reports/([a-f0-9]{16})/ai", self.path)
        if self.path not in ("/api/analyze", "/api/demo", "/api/updates/check",
                             "/api/projects/connect", "/api/projects/pick-folder",
                             "/api/ai/download") and not (project_audit or report_ai):
            return self._error(HTTPStatus.NOT_FOUND, "Not found")
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            return self._error(HTTPStatus.BAD_REQUEST, "Invalid request length")
        if not 0 <= size <= MAX_REQUEST_BYTES:
            self.close_connection = True
            return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request exceeds 25 MiB")
        try:
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("JSON object expected")
            if self.path == "/api/ai/download":
                model = payload.get("model", "")
                if not isinstance(model, str) or model not in INSTALLABLE_MODELS:
                    raise ValueError("Choose an approved small coding model")
                with self.server.model_install_lock:
                    if self.server.model_install["state"] == "downloading":
                        return self._error(HTTPStatus.CONFLICT, "A model download is already running")
                    self.server.model_install = {"state": "downloading", "model": model,
                                                 "phase": "Contacting local Ollama",
                                                 "downloaded": 0, "total": 0}
                server = self.server
                def worker():
                    with server.jobs_lock:
                        server.active_jobs += 1
                    def update(fields):
                        with server.model_install_lock:
                            server.model_install.update(fields)
                    try:
                        pull_model(model, update)
                        update({"state": "complete", "phase": "success"})
                    except ValueError:
                        update({"state": "failed", "phase": "Check Ollama and network"})
                    finally:
                        with server.jobs_lock:
                            server.active_jobs -= 1
                threading.Thread(target=worker, name="bugcircuit-ollama-download", daemon=True).start()
                return self._json(HTTPStatus.ACCEPTED, {"started": True, "model": model})
            if self.path == "/api/projects/pick-folder":
                choice = choose_local_folder()
                return self._json(HTTPStatus.OK, {"path": choice})
            if self.path == "/api/projects/connect":
                mode = payload.get("mode")
                if mode == "folder":
                    item = self.server.projects.connect_folder(payload.get("path", ""))
                elif mode == "github":
                    item = self.server.projects.connect_public(payload.get("url", ""))
                else:
                    raise ValueError("Select GitHub URL or local repository folder")
                return self._json(HTTPStatus.CREATED, {"project": item})
            if project_audit:
                with self.server.jobs_lock:
                    self.server.active_jobs += 1
                try:
                    entry = self.server.projects.get(project_audit.group(1))
                    report = audit_project(entry)
                    ident = secrets.token_hex(8)
                    export_report(report, self.server.reports_dir / ident)
                    return self._json(HTTPStatus.CREATED, {"report": summary(report.as_dict(), ident)})
                finally:
                    with self.server.jobs_lock:
                        self.server.active_jobs -= 1
            if report_ai:
                folder = self._report_path(report_ai.group(1))
                file = folder / "report.json" if folder else None
                if not file or not file.is_file():
                    return self._error(HTTPStatus.NOT_FOUND, "Report not found")
                with self.server.jobs_lock:
                    self.server.active_jobs += 1
                try:
                    result = explain_with_ollama(json.loads(file.read_text(encoding="utf-8")),
                                                 payload.get("model", ""))
                    return self._json(HTTPStatus.OK, {"analysis": result, "provider": "ollama-local",
                                                      "warning": "AI suggestions are unverified; no source files were sent."})
                finally:
                    with self.server.jobs_lock:
                        self.server.active_jobs -= 1
            if self.path == "/api/updates/check":
                from .updater import request_path
                request_path().write_text("check", encoding="utf-8")
                return self._json(HTTPStatus.ACCEPTED, {"queued": True})
            with self.server.jobs_lock:
                self.server.active_jobs += 1
            try:
                if self.path == "/api/demo":
                    events, warnings, source = self._demo()
                else:
                    events, warnings, source = self._analyze_input(payload)
                report = analyze(events, source=source, warnings=warnings)
                report_id = secrets.token_hex(8)
                folder = self.server.reports_dir / report_id
                export_report(report, folder)
                self._json(HTTPStatus.CREATED, {"report": summary(report.as_dict(), report_id)})
            finally:
                with self.server.jobs_lock:
                    self.server.active_jobs -= 1
        except (ValueError, TypeError, ScopeError, UnicodeError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc)[:240])
        except Exception:
            # Do not expose stack traces, filesystem paths or unexpected internal details.
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Analysis could not be completed")

    @staticmethod
    def _demo():
        return [Event(id="E0001", kind="http", method="GET", status=400,
                      url="https://demo.example/callback", error="OAuth state mismatch")], \
               ["Synthetic demo data, not a real website scan."], "Synthetic OAuth demo"

    @staticmethod
    def _analyze_input(payload: dict):
        kind = payload.get("kind")
        if kind == "http":
            url = payload.get("url", "")
            if not isinstance(url, str) or len(url) > 2000:
                raise ValueError("Valid URL required")
            if payload.get("authorized") is not True:
                raise ValueError("Confirm that you are authorized to inspect this URL")
            parsed = urlsplit(url)
            events, warnings = inspect_url(url, max_redirects=3)
            return events, warnings, "HTTP probe: " + (parsed.hostname or "unknown")
        if kind not in ("har", "workflow", "otel"):
            raise ValueError("Unsupported analysis mode")
        raw = payload.get("contents")
        if not isinstance(raw, str):
            raise ValueError("Upload a UTF-8 JSON file")
        max_bytes = {"har": MAX_HAR_BYTES, "workflow": 10 * 1024 * 1024,
                     "otel": 20 * 1024 * 1024}[kind]
        if len(raw.encode("utf-8")) > max_bytes:
            raise ValueError("File is too large for this format")
        try:
            content = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("File is not valid JSON") from exc
        engines = {"har": (parse_har, "HAR upload"),
                   "workflow": (parse_workflow, "Workflow upload"),
                   "otel": (parse_otlp, "OpenTelemetry upload")}
        parse, name = engines[kind]
        events, warnings = parse(content)
        return events, warnings, name + " (local)"

    def do_DELETE(self) -> None:
        if not self._trusted_request(modifying=True):
            return
        forgotten = re.fullmatch(r"/api/projects/([a-f0-9]{16})", self.path)
        if forgotten:
            try:
                self.server.projects.forget(forgotten.group(1))
                return self._json(HTTPStatus.OK, {"forgotten": True, "files_preserved": True})
            except ValueError:
                return self._error(HTTPStatus.NOT_FOUND, "Project not found")
        match = re.fullmatch(r"/api/reports/([a-f0-9]{16})", self.path)
        if not match:
            return self._error(HTTPStatus.NOT_FOUND, "Not found")
        folder = self._report_path(match.group(1))
        if not folder or not folder.is_dir():
            return self._error(HTTPStatus.NOT_FOUND, "Report missing")
        for filename in ("report.html", "report.json"):
            (folder / filename).unlink(missing_ok=True)
        folder.rmdir()
        self._json(HTTPStatus.OK, {"deleted": True})


def serve(port: int = 8765, open_browser: bool = False, directory: Path | None = None):
    server = LocalServer(("127.0.0.1", port), directory=directory)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"BugCircuit v{__version__} is running: {url}")
    print("Local-only mode. Keep this window open; press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
