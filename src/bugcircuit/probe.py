"""Bounded single-target HTTP diagnostics with per-hop allowlisting.

This is not a scanner or crawler. DNS validation is best-effort; for sensitive
networks, run from an isolated container with egress restrictions.
"""

import ipaddress
import socket
import time
from urllib.parse import urljoin, urlsplit

import httpx

from .models import Event
from .redact import header_summary, safe_text, safe_url


class ScopeError(ValueError):
    pass


def validate_target(url: str, allowed_hosts: set[str], allow_private: bool = False) -> None:
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower().rstrip(".")
        port = p.port  # validates malformed ports
    except ValueError as exc:
        raise ScopeError("Invalid URL or port") from exc
    if p.scheme not in ("http", "https") or not host or p.username or p.password:
        raise ScopeError("Only credential-free HTTP(S) URLs are allowed")
    if host not in allowed_hosts:
        raise ScopeError(f"Out-of-scope hostname: {host}")
    if port not in (None, 80, 443) and not allow_private:
        raise ScopeError("Nonstandard ports require --allow-private")
    try:
        addr = ipaddress.ip_address(host)
        ips = [addr]
    except ValueError:
        try:
            ips = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(
                host, port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)]
        except (socket.gaierror, OSError) as exc:
            raise ScopeError(f"DNS resolution failed for {host}") from exc
    if not ips:
        raise ScopeError("Host did not resolve to an IP address")
    if not allow_private and any(not ip.is_global for ip in ips):
        raise ScopeError("Non-public IP targets require --allow-private")


def inspect_url(url: str, *, extra_hosts: list[str] | None = None,
                allow_private: bool = False, max_redirects: int = 5,
                timeout: float = 10.0, client: httpx.Client | None = None
                ) -> tuple[list[Event], list[str]]:
    """Run at most 1 + max_redirects GETs, never submit cookies, tokens or bodies."""
    parsed = urlsplit(url)
    allowed = {((parsed.hostname or "").lower().rstrip("."))}
    allowed.update(h.lower().rstrip(".") for h in (extra_hosts or []))
    events: list[Event] = []
    warnings = ["Only GET requests are sent. No credentials or request bodies are supplied.",
                "DNS validation is best-effort; use network egress isolation for untrusted targets."]
    current = url
    seen: set[str] = set()
    own_client = client is None
    client = client or httpx.Client(follow_redirects=False, timeout=timeout, trust_env=False,
                                   headers={"User-Agent": "BugCircuit/0.1 (authorized diagnostics)"})
    try:
        for index in range(max_redirects + 1):
            validate_target(current, allowed, allow_private)
            if current in seen:
                warnings.append("Repeated redirect destination; further requests stopped.")
                break
            seen.add(current)
            try:
                started = time.perf_counter()
                with client.stream("GET", current, follow_redirects=False) as response:
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                    next_location = response.headers.get("location", "")
                    redirected_to = urljoin(str(response.url), next_location) if next_location else ""
                    events.append(Event(id=f"E{index+1:04}", kind="http", url=safe_url(current),
                                        method="GET", status=response.status_code,
                                        duration_ms=elapsed_ms,
                                        location=safe_url(redirected_to) if redirected_to else "",
                                        headers=header_summary(dict(response.headers))))
                    if response.status_code not in (301, 302, 303, 307, 308) or not redirected_to:
                        break
                    # Block before following a new origin (or a private-network transition).
                    try:
                        validate_target(redirected_to, allowed, allow_private)
                    except ScopeError as exc:
                        warnings.append("Redirect not followed: " + safe_text(exc))
                        break
                    if index == max_redirects:
                        warnings.append("Redirect budget exhausted.")
                        break
                    current = redirected_to
            except httpx.HTTPError as exc:
                events.append(Event(id=f"E{index+1:04}", kind="requestfailed", url=safe_url(current),
                                    method="GET", error=safe_text(type(exc).__name__ + ": " + str(exc))))
                break
    finally:
        if own_client:
            client.close()
    return events, warnings
