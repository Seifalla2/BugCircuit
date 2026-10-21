"""Safe, standalone HTML and machine-readable JSON reports."""

import html
import json
from pathlib import Path

from .models import Report


def export_report(report: Report, output: Path) -> tuple[Path, Path]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "report.json"
    html_path = output / "report.html"
    json_path.write_text(json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    items = []
    for finding in report.findings:
        suggestions = "".join(f"<li>{html.escape(s)}</li>" for s in finding.recommendations)
        items.append(f'''<article class="finding">
          <div class="finding-top"><span class="pill {html.escape(finding.severity)}">{html.escape(finding.severity)}</span>
          <code>{html.escape(finding.code)}</code><span class="confidence">Evidence: {html.escape(finding.confidence)}</span></div>
          <h3>{html.escape(finding.title)}</h3><p>{html.escape(finding.explanation)}</p>
          <div class="subtitle">Event references: {html.escape(', '.join(finding.evidence_ids))}</div>
          <strong>Recommended checks</strong><ul>{suggestions}</ul>
        </article>''')
    rows = "".join(
        f"<tr><td><code>{html.escape(e.id)}</code></td><td>{html.escape(e.kind)}</td>"
        f"<td>{html.escape(e.method)}</td><td>{html.escape(str(e.status or '—'))}</td>"
        f"<td class='url'>{html.escape(e.url)}</td><td>{html.escape(e.error)}</td></tr>"
        for e in report.events
    )
    warnings = "".join(f"<li>{html.escape(w)}</li>" for w in report.warnings)
    content = '''<!doctype html><html lang="en"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>BugCircuit • Diagnostic Report</title><style>
    :root{color-scheme:dark;font-family:Inter,system-ui,-apple-system,sans-serif}
    *{box-sizing:border-box}body{background:#0c101a;color:#ebefff;margin:0;line-height:1.55}
    main{width:min(1100px,94vw);margin:45px auto 80px}.top{display:flex;align-items:center;gap:15px}
    .mark{background:#9b78ff;color:#111;border-radius:14px;padding:9px 16px;font-size:22px}
    h1{font-size:clamp(1.7rem,4vw,2.6rem);margin:15px 0 8px}h2{margin-top:35px}
    .muted,.subtitle,.confidence{color:#aab2c8}.stats{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}
    .stat,.finding,.notice{background:#151c2b;border:1px solid #2e3850;border-radius:16px;padding:20px}
    .stat{min-width:145px}.stat strong{display:block;font-size:28px}.stat small{color:#aab2c8}
    .finding{margin:13px 0}.finding h3{margin:12px 0 6px}.finding p{margin:0 0 10px}
    .finding-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.pill{border-radius:6px;padding:3px 9px;font-weight:700}
    .high{background:#562831;color:#ffa2a8}.medium{background:#483b1c;color:#f9ce86}
    .low{background:#1f354e;color:#93c6ff}.confidence{font-size:12px}
    code{color:#c7b1ff}table{border-collapse:collapse;width:100%;font-size:13px}
    th,td{text-align:left;padding:12px;border-bottom:1px solid #2e3850;vertical-align:top}
    .table{overflow:auto;background:#151c2b;border-radius:14px;border:1px solid #2e3850}
    .url{max-width:470px;overflow-wrap:anywhere}ul{margin:8px 0}.foot{margin-top:30px;font-size:12px;color:#aab2c8}
    </style></head><body><main><div class="top"><div class="mark">⚡</div><b>BUGCIRCUIT / EVIDENCE FIRST</b></div>
    <h1>Diagnostic Report</h1><p class="muted">Source: __SOURCE__ · Generated: __DATE__</p>
    <div class="stats"><div class="stat"><strong>__EVENTS__</strong><small>Events</small></div>
    <div class="stat"><strong>__FINDINGS__</strong><small>Findings</small></div>
    <div class="stat"><strong>__HIGH__</strong><small>High-severity findings</small></div></div>
    <h2>Findings</h2>__CARDS__<h2>Evidence timeline</h2><div class="table"><table>
    <thead><tr><th>ID</th><th>Type</th><th>Method</th><th>HTTP</th><th>URL</th><th>Error</th></tr></thead>
    <tbody>__ROWS__</tbody></table></div><h2>Warnings &amp; limitations</h2><div class="notice"><ul>__WARNINGS__</ul></div>
    <p class="foot">BugCircuit v0.4 · Heuristic rules are not proof of root cause. No automatic repairs.</p></main></body></html>'''
    replacements = {
        "__SOURCE__": html.escape(report.source), "__DATE__": html.escape(report.generated_at),
        "__EVENTS__": str(len(report.events)), "__FINDINGS__": str(len(report.findings)),
        "__HIGH__": str(sum(1 for f in report.findings if f.severity == "high")),
        "__CARDS__": "".join(items) or "<p class='muted'>No matching findings; absence of findings does not prove health.</p>",
        "__ROWS__": rows, "__WARNINGS__": warnings,
    }
    for key, value in replacements.items():
        content = content.replace(key, value)
    html_path.write_text(content, encoding="utf-8")
    return json_path, html_path
