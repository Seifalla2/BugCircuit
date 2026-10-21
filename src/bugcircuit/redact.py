"""Conservative sanitization of all emitted diagnostics artifacts.

Default policy: drop URL query values, URL credentials and fragments; store only a
minimal response-header allowlist. Do not write raw HAR files to output folders.
"""

import re
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

_SAFE_HEADERS = {"content-type", "access-control-allow-origin", "access-control-allow-credentials", "retry-after"}
_SECRET_KEY = re.compile(r"(?i)(access[_-]?token|refresh[_-]?token|secret|password|passwd|api[_-]?key|authorization|cookie|session|credential|client_secret|jwt|bearer|code|state|key)")
_SECRET_INLINE = re.compile(
    r"(?i)\b(bearer\s+)[a-z0-9._~+/-]+=*|\b((?:token|secret|password|api[_-]?key|authorization|cookie|code|state)\s*[:=]\s*)[^\s&;,]+"
)
_EMAIL = re.compile(r"(?i)[\w.+'-]+@[\w.-]+\.[a-z]{2,}")
_LONG_SEGMENT = re.compile(r"(?<![\w-])[A-Za-z0-9_-]{32,}(?![\w-])")
_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def safe_text(value: object, limit: int = 300) -> str:
    """Remove common secret patterns from exception/console strings."""
    text = str(value or "")
    text = _URL_IN_TEXT.sub(lambda m: safe_url(m.group(0)), text)
    text = _SECRET_INLINE.sub(lambda m: (m.group(1) or m.group(2) or "") + "[REDACTED]", text)
    text = _EMAIL.sub("[EMAIL]", text)
    text = _LONG_SEGMENT.sub("[REDACTED]", text)
    return text[:limit]


def safe_url(raw: object) -> str:
    try:
        parts = urlsplit(str(raw or ""))
        if not parts.scheme or not parts.hostname:
            # A relative Location URL can still carry arbitrary secret query values.
            if parts.query:
                query = "&".join(f"{quote(k)}=REDACTED" for k, _ in parse_qsl(
                    parts.query, keep_blank_values=True)[:30])
                return urlunsplit(("", "", safe_text(parts.path, 160), query, ""))
            return safe_text(raw, 160)
        host = parts.hostname.lower()
        # Restore IPv6 brackets, drop username/password from authority.
        host = f"[{host}]" if ":" in host else host
        port = f":{parts.port}" if parts.port is not None else ""
        path = "/".join(safe_text(segment, 160) for segment in parts.path.split("/"))
        # Never preserve URL query *values*, even for unrecognized keys.
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        query = "&".join(f"{quote(safe_text(key, 48))}=REDACTED" for key, _ in pairs[:30])
        return urlunsplit((parts.scheme.lower(), host + port, path, query, ""))[:1500]
    except (TypeError, ValueError):
        return "[INVALID URL]"


def query_names(raw: str) -> set[str]:
    try:
        return {k.lower() for k, _ in parse_qsl(urlsplit(raw).query, keep_blank_values=True)}
    except ValueError:
        return set()


def header_summary(headers: list[dict] | dict | None) -> dict[str, str]:
    if isinstance(headers, dict):
        items = headers.items()
    elif isinstance(headers, list):
        items = ((h.get("name", ""), h.get("value", "")) for h in headers if isinstance(h, dict))
    else:
        return {}
    result = {}
    for name, value in items:
        key = str(name).lower()
        if key in _SAFE_HEADERS:
            result[key] = safe_text(value, 120)
    return result
