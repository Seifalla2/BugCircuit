"""Read-only Playwright DOM layout checks: no screenshots or HTML snapshots persisted."""

from .models import Event

# Rendered in the inspected page only; layout checks never click, type or edit DOM.
LAYOUT_SCRIPT = r"""() => {
 const vw = document.documentElement.clientWidth;
 const sh = document.documentElement.scrollWidth;
 const hits = [];
 for (const el of document.querySelectorAll('body *')) {
   if (hits.length >= 25) break;
   const r = el.getBoundingClientRect();
   const s = getComputedStyle(el);
   if (s.display === 'none' || s.visibility === 'hidden' || r.width < 1 || r.height < 1) continue;
   if (r.left < -2 || r.right > vw + 2) {
     const tag = el.tagName.toLowerCase();
     const part = (el.id ? '#' + el.id.slice(0,32) : '') +
       (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0,2).join('.') : '');
     hits.push({tag, selector:tag+part, left:Math.round(r.left), right:Math.round(r.right)});
   }
 }
 return {viewport:vw, scrollWidth:sh, overflow:sh>vw+2, hits};
}"""


def layout_events(result: dict, *, viewport_name: str) -> list[Event]:
    """Convert a bounded JS result to sanitized findings input."""
    from .redact import safe_text
    if not isinstance(result, dict) or not result.get("overflow"):
        return []
    vw = int(result.get("viewport") or 0)
    sw = int(result.get("scrollWidth") or 0)
    hits = result.get("hits", [])
    elements = ", ".join(safe_text(h.get("selector", ""), 64) for h in hits[:5]
                         if isinstance(h, dict)) if isinstance(hits, list) else ""
    return [Event(id="", kind="layout", method=viewport_name,
                  error=f"Horizontal overflow observed (viewport {vw}px, document {sw}px); elements: {elements}")]
