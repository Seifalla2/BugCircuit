"""Typed, sanitized outputs. No raw request bodies, cookies, or auth headers are stored."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Event:
    id: str
    kind: str
    url: str = ""
    method: str = ""
    status: int | None = None
    timestamp: str = ""
    duration_ms: float | None = None
    location: str = ""
    error: str = ""
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Finding:
    code: str
    title: str
    severity: str
    confidence: str
    explanation: str
    evidence_ids: list[str]
    recommendations: list[str]


@dataclass
class Report:
    source: str
    events: list[Event]
    findings: list[Finding]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = "1.0"
    tool_version: str = "0.3.0"
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
