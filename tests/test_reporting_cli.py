import json
from pathlib import Path

from bugcircuit.cli import main

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_cli_produces_sanitized_json_and_html(tmp_path):
    assert main(["analyze-har", str(EXAMPLES / "oauth-state-mismatch.har"),
                 "--out", str(tmp_path)]) == 0
    js = (tmp_path / "report.json").read_text()
    document = (tmp_path / "report.html").read_text()
    assert json.loads(js)["schema_version"] == "1.0"
    assert "OAUTH_STATE_MISMATCH" in js and "OAUTH_STATE_MISMATCH" in document
    for secret in ("TOP-SECRET", "VERY-SECRET", "SECRET-TOKEN", "session=PRIVATE"):
        assert secret not in js and secret not in document


def test_invalid_file_exit_status(tmp_path):
    assert main(["analyze-har", str(tmp_path / "missing.har")]) == 2


def test_invalid_redirect_limit(tmp_path):
    assert main(["inspect", "https://example.com", "--max-redirects", "100",
                 "--out", str(tmp_path)]) == 2


def test_report_html_escapes_untrusted_content(tmp_path):
    from bugcircuit.analyze import analyze
    from bugcircuit.models import Event
    from bugcircuit.reporting import export_report
    event = Event("E0001", "console", error="Uncaught <script>alert('injected')</script>")
    _, html_path = export_report(analyze([event], "<img src=x onerror=alert(1)>") , tmp_path)
    text = html_path.read_text()
    assert "<script>alert('injected')</script>" not in text
    assert "<img src=x onerror=alert(1)>" not in text
    assert "&lt;script&gt;" in text
