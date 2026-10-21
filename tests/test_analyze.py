from pathlib import Path

from bugcircuit.analyze import analyze
from bugcircuit.har import read_har
from bugcircuit.models import Event

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_oauth_findings_have_distinct_evidence():
    events, warnings = read_har(EXAMPLES / "oauth-state-mismatch.har")
    report = analyze(events, "synthetic", warnings)
    codes = {f.code for f in report.findings}
    assert "AUTH_CALLBACK_FAILED" in codes
    assert "OAUTH_STATE_MISMATCH" in codes
    for finding in report.findings:
        assert finding.evidence_ids
        assert finding.recommendations


def test_api_statuses():
    events, _ = read_har(EXAMPLES / "api-failures.har")
    report = analyze(events, "synthetic")
    assert {f.code for f in report.findings} == {
        "HTTP_AUTH_REJECTED", "HTTP_SERVER_ERROR", "HTTP_RATE_LIMIT"}


def test_redirect_cycle_requires_observed_edges():
    events = [Event("E0001", "http", url="https://a.test/a", status=302, location="https://a.test/b"),
              Event("E0002", "http", url="https://a.test/b", status=302, location="https://a.test/a")]
    report = analyze(events, "synthetic")
    assert "REDIRECT_CYCLE" in {f.code for f in report.findings}


def test_failed_request_is_not_assumed_to_be_cors():
    report = analyze([Event("E0001", "requestfailed", error="Failed to fetch")], "synthetic")
    assert "BROWSER_NETWORK_FAILURE" in {f.code for f in report.findings}
    assert "BROWSER_CORS_BLOCK" not in {f.code for f in report.findings}


def test_empty_is_not_reported_as_healthy():
    report = analyze([], "synthetic")
    assert not report.findings
    assert any("No diagnostic events" in w for w in report.warnings)


def test_redacted_query_does_not_create_a_false_redirect_cycle():
    events = [Event("E0001", "http", url="https://a.test/a?state=REDACTED",
                    status=302, location="https://a.test/b?state=REDACTED"),
              Event("E0002", "http", url="https://a.test/b?state=REDACTED",
                    status=302, location="https://a.test/a?state=REDACTED")]
    report = analyze(events, "synthetic")
    assert "REDIRECT_CYCLE" not in {f.code for f in report.findings}
