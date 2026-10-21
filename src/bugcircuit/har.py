"""Import the minimum evidence required from a HAR file, discarding sensitive fields."""

import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from .models import Event
from .redact import header_summary, query_names, safe_text, safe_url

MAX_HAR_BYTES = 25 * 1024 * 1024
MAX_EVENTS = 5000


class TraceError(ValueError):
    pass


def read_har(path: Path) -> tuple[list[Event], list[str]]:
    path = Path(path)
    if path.stat().st_size > MAX_HAR_BYTES:
        raise TraceError("HAR exceeds the 25 MiB import limit")
    try:
        with path.open(encoding="utf-8") as f:
            data: Any = json.load(f)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise TraceError("HAR is not valid UTF-8 JSON") from exc
    return parse_har(data)


def parse_har(data: Any) -> tuple[list[Event], list[str]]:
    """Inspect an already decoded HAR without writing the original trace to disk."""
    if not isinstance(data, dict) or not isinstance(data.get("log"), dict):
        raise TraceError("Expected a HAR object with a 'log' field")
    entries = data["log"].get("entries")
    if not isinstance(entries, list):
        raise TraceError("Expected 'log.entries' array")
    if len(entries) > MAX_EVENTS:
        raise TraceError(f"Trace exceeds {MAX_EVENTS} entries")
    result: list[Event] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        req = entry.get("request") if isinstance(entry.get("request"), dict) else {}
        resp = entry.get("response") if isinstance(entry.get("response"), dict) else {}
        raw_url = str(req.get("url", ""))
        if not raw_url:
            continue
        raw_headers = resp.get("headers")
        headers = header_summary(raw_headers)
        try:
            status = int(resp.get("status"))
            if status < 0 or status > 599:
                status = None
        except (TypeError, ValueError, OverflowError):
            status = None
        try:
            raw_duration = float(entry.get("time", 0))
            duration = round(max(0.0, raw_duration), 2) if math.isfinite(raw_duration) else None
        except (TypeError, ValueError, OverflowError):
            duration = None
        redirect = resp.get("redirectURL", "")
        if not redirect and isinstance(raw_headers, list):
            redirect = next((h.get("value", "") for h in raw_headers if isinstance(h, dict)
                             and str(h.get("name", "")).lower() == "location"), "")
        event = Event(
            id=f"E{index:04}",
            kind="http",
            url=safe_url(raw_url),
            method=safe_text(req.get("method", "GET"), 16).upper(),
            status=status,
            timestamp=safe_text(entry.get("startedDateTime", ""), 40),
            duration_ms=duration,
            location=safe_url(urljoin(raw_url, str(redirect))) if redirect else "",
            error=safe_text(entry.get("_failureText") or entry.get("_error") or ""),
            headers=headers,
        )
        # Error query name is diagnostic; never store its value.
        if "error" in query_names(raw_url):
            event.error = (event.error + "; OAuth error query parameter present").strip("; ")
        result.append(event)
    return result, ["HAR request/response bodies, cookies, and authorization headers were not imported."]
