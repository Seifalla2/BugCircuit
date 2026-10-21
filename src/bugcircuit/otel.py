"""Bounded, offline OTLP JSON span importer. Never copies arbitrary attributes."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Event
from .redact import safe_text, safe_url

MAX_OTLP_BYTES = 20 * 1024 * 1024
MAX_OTLP_SPANS = 5000


def _attribute(attributes: object, key: str) -> str:
    """Read only an explicitly allowed semantic-convention attribute."""
    if not isinstance(attributes, list):
        return ""
    for attr in attributes:
        if isinstance(attr, dict) and attr.get("key") == key:
            value = attr.get("value")
            if isinstance(value, dict):
                for field in ("stringValue", "intValue"):
                    if field in value:
                        return str(value[field])[:2000]
    return ""


def _time(ns: object) -> str:
    try:
        value = int(ns)
        if value < 0 or value > 100_000_000_000_000_000_000:
            return ""
        return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def read_otlp(path: Path) -> tuple[list[Event], list[str]]:
    """Import OTLP resourceSpans/scopeSpans/spans; exclude bodies, IDs and arbitrary tags."""
    path = Path(path)
    if path.stat().st_size > MAX_OTLP_BYTES:
        raise ValueError("OTLP trace exceeds 20 MiB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid UTF-8 OTLP JSON") from exc
    return parse_otlp(data)


def parse_otlp(data: object) -> tuple[list[Event], list[str]]:
    """Inspect decoded OTLP spans in memory, without persisting source payloads."""
    if not isinstance(data, dict) or not isinstance(data.get("resourceSpans"), list):
        raise ValueError("Expected OTLP JSON object with resourceSpans array")  # noqa: TRY004 - stable CLI contract
    events = []
    for resource in data["resourceSpans"]:
        if not isinstance(resource, dict):
            continue
        for scope in resource.get("scopeSpans", []):
            if not isinstance(scope, dict):
                continue
            for span in scope.get("spans", []):
                if not isinstance(span, dict):
                    continue
                if len(events) >= MAX_OTLP_SPANS:
                    raise ValueError("OTLP trace exceeds 5000 spans")
                attributes = span.get("attributes", [])
                http_status = (_attribute(attributes, "http.response.status_code")
                               or _attribute(attributes, "http.status_code"))
                method = (_attribute(attributes, "http.request.method")
                          or _attribute(attributes, "http.method"))
                url = (_attribute(attributes, "url.full")
                       or _attribute(attributes, "http.url"))
                try:
                    status = int(http_status) if http_status else None
                    if status is not None and not 100 <= status <= 599:
                        status = None
                except (TypeError, ValueError):
                    status = None
                state = span.get("status", {})
                is_error = isinstance(state, dict) and state.get("code") in (2, "2", "STATUS_CODE_ERROR")
                raw_error = state.get("message", "") if is_error else ""
                if is_error and not raw_error:
                    raw_error = "OpenTelemetry span marked ERROR"
                start, end = span.get("startTimeUnixNano"), span.get("endTimeUnixNano")
                try:
                    delta = (int(end) - int(start)) / 1_000_000
                    duration = round(delta, 2) if 0 <= delta <= 86_400_000 else None
                except (ValueError, TypeError, OverflowError):
                    duration = None
                events.append(Event(
                    id=f"E{len(events)+1:04}", kind="http" if status else "span",
                    url=safe_url(url) if url else "",
                    method=safe_text(method or span.get("name", ""), 80),
                    status=status, timestamp=_time(start), duration_ms=duration,
                    error=safe_text(raw_error, 300),
                ))
    return events, ["Only selected HTTP attributes and span error status were imported.",
                    "Trace IDs, raw resource attributes, events and payloads were discarded."]
