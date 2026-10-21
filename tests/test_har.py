import json
from pathlib import Path

import pytest

from bugcircuit.har import TraceError, read_har

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_har_sanitizes_oauth_and_preserves_evidence():
    events, warnings = read_har(EXAMPLES / "oauth-state-mismatch.har")
    assert len(events) == 2
    assert events[1].status == 400
    assert events[1].error == "OAuth state mismatch"
    assert "VERY-SECRET" not in json.dumps([e.__dict__ for e in events])
    assert "TOP-SECRET" not in json.dumps([e.__dict__ for e in events])
    assert "session=PRIVATE" not in json.dumps([e.__dict__ for e in events])
    assert warnings


def test_malformed_har_rejected(tmp_path):
    p = tmp_path / "trace.har"
    p.write_text('{"wrong":"shape"}')
    with pytest.raises(TraceError):
        read_har(p)


def test_event_budget_is_enforced(tmp_path):
    p = tmp_path / "oversized.har"
    p.write_text(json.dumps({"log": {"entries": [{}] * 5001}}))
    with pytest.raises(TraceError):
        read_har(p)


def test_nan_duration_does_not_pollute_json(tmp_path):
    p = tmp_path / "nan.har"
    p.write_text(json.dumps({"log": {"entries": [{"time": float("nan"),
        "request": {"url": "https://example.test"}, "response": {"status": 200}}]}}))
    events, _ = read_har(p)
    assert events[0].duration_ms is None
