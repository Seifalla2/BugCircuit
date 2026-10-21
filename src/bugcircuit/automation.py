"""Offline analysis of *synthetic or user-provided* workflow execution event exports.

Accepted format: {"executions":[{"id":"...", "workflow":"...", "status":"failed",
"attempt":1, "duration_ms":1000, "trigger_id":"...", "error":"..."}, ...]}.
Event bodies and input/output payloads are never copied to reports.
"""

import json
from pathlib import Path

from .models import Event
from .redact import safe_text

MAX_WORKFLOW_BYTES = 10 * 1024 * 1024
MAX_EXECUTIONS = 5000
VALID_STATUSES = {"success", "failed", "timeout", "running", "cancelled", "retried"}


def read_workflow(path: Path) -> tuple[list[Event], list[str]]:
    path = Path(path)
    if path.stat().st_size > MAX_WORKFLOW_BYTES:
        raise ValueError("Workflow export exceeds 10 MiB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Workflow export must contain valid UTF-8 JSON") from exc
    return parse_workflow(data)


def parse_workflow(data: object) -> tuple[list[Event], list[str]]:
    """Inspect decoded workflow exports in memory, discarding payloads."""
    if not isinstance(data, dict) or not isinstance(data.get("executions"), list):
        raise ValueError("Expected JSON object with executions array")  # noqa: TRY004 - stable CLI contract
    if len(data["executions"]) > MAX_EXECUTIONS:
        raise ValueError("Workflow export exceeds 5000 executions")
    events = []
    for row in data["executions"]:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "")).lower()
        if status not in VALID_STATUSES:
            continue
        workflow = safe_text(row.get("workflow", "unnamed"), 60)
        trigger_id = safe_text(row.get("trigger_id", ""), 64)
        # Trigger ID is diagnostic but can be personal data. Hash it deterministically
        # within this report so duplicates can be correlated without exposing raw IDs.
        import hashlib
        trigger_hash = hashlib.sha256(trigger_id.encode()).hexdigest()[:16] if trigger_id else ""
        try:
            duration = float(row.get("duration_ms", 0))
            if duration < 0 or duration > 86_400_000 or not __import__("math").isfinite(duration):
                duration = None
        except (ValueError, TypeError):
            duration = None
        events.append(Event(
            id=f"E{len(events)+1:04}", kind="workflow", method=status.upper(),
            url="", timestamp=safe_text(row.get("timestamp", ""), 40),
            duration_ms=duration, error=safe_text(row.get("error", "")),
            headers={"workflow": workflow, "trigger_fingerprint": trigger_hash},
        ))
    return events, ["Payloads, API keys, input/output and original trigger IDs were not imported.",
                    "Workflow findings are symptoms; retries/idempotency require backend verification."]
