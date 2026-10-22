import json
from pathlib import Path

import pytest

from bugcircuit.analyze import analyze
from bugcircuit.cli import main
from bugcircuit.otel import read_otlp

FIXTURE = Path(__file__).parent.parent / "examples/otel-errors.json"


def test_otlp_http_and_backend_evidence():
    events, warnings = read_otlp(FIXTURE)
    assert len(events) == 2
    assert events[0].status == 503
    assert events[0].duration_ms == 120
    assert events[0].url.endswith("access_token=REDACTED")
    assert "FAKE_SECRET" not in json.dumps([e.__dict__ for e in events])
    report = analyze(events, "synthetic", warnings)
    assert {f.code for f in report.findings} >= {"HTTP_SERVER_ERROR", "OTEL_SPAN_FAILURE"}


def test_otlp_drops_ids_and_arbitrary_tags():
    events, _ = read_otlp(FIXTURE)
    data = json.dumps([e.__dict__ for e in events])
    assert "FAKE_PRIVATE_ID" not in data
    assert "synthetic-api" not in data


def test_otlp_malformed_shape(tmp_path):
    file = tmp_path / "invalid.json"
    file.write_text('{"resourceSpans": null}')
    with pytest.raises(ValueError):
        read_otlp(file)


def test_otlp_cli(tmp_path):
    assert main(["analyze-otel", str(FIXTURE), "--out", str(tmp_path)]) == 0
    assert (tmp_path / "report.html").exists()
