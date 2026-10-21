"""CLI entrypoint: offline HAR, bounded live HTTP, or optional browser capture."""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__
from .analyze import analyze
from .har import TraceError, read_har
from .probe import ScopeError, inspect_url
from .reporting import export_report


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bugcircuit", description="Evidence-first web diagnostics.")
    p.add_argument("--version", action="version", version=f"bugcircuit {__version__}")
    commands = p.add_subparsers(dest="command", required=True)
    har = commands.add_parser("analyze-har", help="Safely analyze an existing HAR trace offline")
    har.add_argument("har", type=Path, help="Path to an authorized HAR file")
    har.add_argument("--out", type=Path, default=Path("bugcircuit-report"))
    inspect = commands.add_parser("inspect", help="GET one authorized URL; limit redirects")
    inspect.add_argument("url")
    inspect.add_argument("--allow-host", action="append", default=[], help="Additional redirect host allowed; repeatable")
    inspect.add_argument("--allow-private", action="store_true", help="Opt in to localhost/private IP and dev ports")
    inspect.add_argument("--max-redirects", type=int, default=5)
    inspect.add_argument("--out", type=Path, default=Path("bugcircuit-report"))
    browser = commands.add_parser("capture", help="Capture a single page with optional Playwright Chromium")
    browser.add_argument("url")
    browser.add_argument("--allow-private", action="store_true")
    browser.add_argument("--wait-ms", type=int, default=750)
    browser.add_argument("--check-layout", action="store_true", help="Read-only DOM overflow test at 375, 768, 1280px")
    browser.add_argument("--out", type=Path, default=Path("bugcircuit-report"))
    wf = commands.add_parser("analyze-workflow", help="Offline workflow execution export diagnostics")
    wf.add_argument("workflow", type=Path, help="JSON export of executions (see docs)")
    wf.add_argument("--out", type=Path, default=Path("bugcircuit-report"))
    ot = commands.add_parser("analyze-otel", help="Offline OTLP JSON trace diagnostics")
    ot.add_argument("otlp", type=Path)
    ot.add_argument("--out", type=Path, default=Path("bugcircuit-report"))
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "analyze-har":
            events, warnings = read_har(args.har)
            source = f"HAR: {args.har.name}"
        elif args.command == "analyze-workflow":
            from .automation import read_workflow
            events, warnings = read_workflow(args.workflow)
            source = f"Workflow export: {args.workflow.name}"
        elif args.command == "analyze-otel":
            from .otel import read_otlp
            events, warnings = read_otlp(args.otlp)
            source = f"OTLP: {args.otlp.name}"
        elif args.command == "inspect":
            if not 0 <= args.max_redirects <= 10:
                raise ValueError("--max-redirects must be between 0 and 10")
            events, warnings = inspect_url(args.url, extra_hosts=args.allow_host,
                                           allow_private=args.allow_private,
                                           max_redirects=args.max_redirects)
            source = f"HTTP probe: {urlsplit(args.url).hostname or '[invalid]'}"
        else:
            from .browser import capture_page
            events, warnings = capture_page(args.url, allow_private=args.allow_private,
                                            wait_ms=args.wait_ms, check_layout=args.check_layout)
            source = f"Browser capture: {urlsplit(args.url).hostname or '[invalid]'}"
        report = analyze(events, source=source, warnings=warnings)
        json_file, html_file = export_report(report, args.out)
        print(f"BugCircuit v{__version__} • {len(events)} events • {len(report.findings)} findings")
        for finding in report.findings:
            print(f"[{finding.severity.upper()}] {finding.code}: {finding.title}")
        print(f"JSON: {json_file.resolve()}\nHTML: {html_file.resolve()}")
        return 0
    except (ScopeError, TraceError, FileNotFoundError, PermissionError, ValueError,
            RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
