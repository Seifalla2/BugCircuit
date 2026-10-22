"""Optional Playwright capture of a single user-authorized page.

No browser storage, cookies, request bodies or raw traces are exported.
Only sanitized event metadata is retained in memory. This is NOT safe for
untrusted pages inside privileged networks; use a sandboxed environment.
"""

import asyncio
from urllib.parse import urlsplit

from .models import Event
from .probe import validate_target
from .redact import safe_text, safe_url


async def _capture(url: str, allow_private: bool, wait_ms: int, check_layout: bool) -> tuple[list[Event], list[str]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Browser extra required: pip install 'bugcircuit[browser]' and playwright install chromium") from exc
    validate_target(url, {(urlsplit(url).hostname or "").lower()}, allow_private)
    events: list[Event] = []
    warnings = ["Browser capture does not store cookies, request/response bodies or secrets.",
                "Browser subresources may use third-party origins. Run in an isolated environment."]
    count = 0

    def record(kind: str, *, address: str = "", status: int | None = None,
               method: str = "", error: str = "") -> None:
        nonlocal count
        if count >= 2000:
            return
        count += 1
        events.append(Event(id=f"E{count:04}", kind=kind, url=safe_url(address) if address else "",
                            method=safe_text(method, 12), status=status, error=safe_text(error)))

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
        except Exception as exc:
            raise RuntimeError(
                "Chromium not available. Run: python -m playwright install chromium"
            ) from exc
        try:
            context = await browser.new_context(accept_downloads=False, service_workers="block")
            page = await context.new_page()
            page.on("response", lambda r: record("http", address=r.url, status=r.status,
                                                  method=r.request.method))
            page.on("requestfailed", lambda r: record("requestfailed", address=r.url,
                                                       method=r.method, error=r.failure or "request failed"))
            page.on("pageerror", lambda exc: record("pageerror", error=str(exc)))
            page.on("console", lambda msg: record("console", error=msg.text)
                    if msg.type == "error" else None)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(wait_ms)
                if check_layout:
                    from .layout import LAYOUT_SCRIPT, layout_events
                    for width in (375, 768, 1280):
                        await page.set_viewport_size({"width": width, "height": 840})
                        await page.wait_for_timeout(75)
                        for ev in layout_events(await page.evaluate(LAYOUT_SCRIPT), viewport_name=str(width)):
                            record("layout", method=ev.method, error=ev.error)
            except Exception as exc:  # noqa: BLE001 - Playwright failures vary by platform
                record("requestfailed", address=url, error=str(exc))
            finally:
                await context.close()
        finally:
            await browser.close()
    if count >= 2000:
        warnings.append("Event limit of 2000 reached; capture truncated.")
    return events, warnings


def capture_page(url: str, *, allow_private: bool = False,
                 wait_ms: int = 750, check_layout: bool = False) -> tuple[list[Event], list[str]]:
    if not 0 <= wait_ms <= 10000:
        raise ValueError("wait_ms must be between 0 and 10000")
    return asyncio.run(_capture(url, allow_private, wait_ms, check_layout))
