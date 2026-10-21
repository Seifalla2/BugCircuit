"""Web UI integration tests; no browser binaries or internet needed."""
import http.client
import json
import threading

import pytest

from bugcircuit.web import LocalServer


@pytest.fixture
def server(tmp_path):
    srv = LocalServer(("127.0.0.1", 0), directory=tmp_path)
    worker = threading.Thread(target=srv.serve_forever, daemon=True)
    worker.start()
    yield srv, tmp_path
    srv.shutdown()
    srv.server_close()
    worker.join(timeout=3)


def call(srv, method, path, payload=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=3)
    req_headers = {"Host": f"127.0.0.1:{srv.server_port}"}
    req_headers.update(headers or {})
    connection.request(method, path, json.dumps(payload) if payload is not None else None,
                       headers=req_headers)
    response = connection.getresponse()
    raw = response.read()
    status = response.status
    ctype = response.getheader("Content-Type")
    connection.close()
    return status, json.loads(raw) if "application/json" in ctype else raw


def json_headers(srv):
    return {"Content-Type": "application/json", "Origin": f"http://localhost:{srv.server_port}"}


def test_web_assets_and_health(server):
    srv, _ = server
    status, body = call(srv, "GET", "/api/health")
    assert status == 200 and body["mode"] == "loopback"
    for path in ["/", "/assets/styles.css", "/assets/app.js", "/favicon.svg"]:
        status, data = call(srv, "GET", path)
        assert status == 200 and data



def test_showcase_is_synthetic_and_does_not_touch_owner_data(server):
    srv, root = server
    for resource in ("/showcase", "/showcase.html", "/assets/showcase.css",
                     "/assets/showcase.js"):
        status, body = call(srv, "GET", resource)
        assert status == 200 and body

    status, payload = call(srv, "GET", "/api/showcase")
    assert status == 200
    assert payload["synthetic"] is True
    assert set(payload["examples"]) == {"oauth", "api", "workflow"}
    oauth = payload["examples"]["oauth"]
    assert "AUTH_CALLBACK_FAILED" in [f["code"] for f in oauth["findings"]]
    assert "OAUTH_STATE_MISMATCH" in [f["code"] for f in oauth["findings"]]
    assert "HTTP_SERVER_ERROR" in [f["code"] for f in payload["examples"]["api"]["findings"]]
    assert "WORKFLOW_TIMEOUTS" in [f["code"] for f in payload["examples"]["workflow"]["findings"]]
    assert all("Synthetic" in report["source"] for report in payload["examples"].values())
    assert not list(root.glob("*/report.json"))
    assert not list(root.glob("*/report.html"))


def test_demo_saved_and_deleted(server):
    srv, root = server
    status, data = call(srv, "POST", "/api/demo", {}, json_headers(srv))
    assert status == 201
    item = data["report"]
    assert item["findings"] >= 2 and item["high"] >= 1
    assert (root / item["id"] / "report.html").is_file()
    status, detail = call(srv, "GET", "/api/reports/" + item["id"])
    assert status == 200 and detail["source"] == "Synthetic OAuth demo"
    status, _ = call(srv, "GET", "/reports/" + item["id"] + ".html")
    assert status == 200
    status, _ = call(srv, "DELETE", "/api/reports/" + item["id"], {}, json_headers(srv))
    assert status == 200
    assert not (root / item["id"]).exists()
    status, _ = call(srv, "GET", "/api/reports/" + item["id"])
    assert status == 404


def test_uploaded_har_sanitizes_raw_data(server):
    srv, root = server
    secret = "Bearer-do-not-save-SECRET321"
    har = {"log": {"entries": [{"request": {"method": "GET", "url": "https://demo.example/private?token=" + secret,
               "headers": [{"name": "Authorization", "value": secret}]},
               "response": {"status": 401, "headers": []}}]}}
    status, data = call(srv, "POST", "/api/analyze", {"kind": "har", "contents": json.dumps(har)}, json_headers(srv))
    assert status == 201 and data["report"]["high"] >= 1
    stored = (root / data["report"]["id"] / "report.json").read_text(encoding="utf-8")
    assert secret not in stored
    assert "Authorization" not in stored
    assert "HTTP_AUTH_REJECTED" in stored
    assert not any(p.name.endswith(".har") for p in root.rglob("*"))


def test_reject_bad_host_origin_and_content_type(server):
    srv, _ = server
    bad_host = {"Host": "attacker.example", "Content-Type": "application/json"}
    assert call(srv, "GET", "/api/health", headers=bad_host)[0] == 403
    assert call(srv, "POST", "/api/demo", {}, {"Content-Type": "application/json", "Origin": "https://evil.example"})[0] == 403
    assert call(srv, "POST", "/api/demo", {}, {"Content-Type": "text/plain"})[0] == 415
    assert call(srv, "GET", "/reports/../../etc/passwd")[0] == 404
    assert call(srv, "DELETE", "/api/reports/not-an-id", {}, json_headers(srv))[0] == 404


def test_http_without_authorization_is_rejected(server):
    srv, _ = server
    status, message = call(srv, "POST", "/api/analyze",
                           {"kind": "http", "url": "https://example.com"}, json_headers(srv))
    assert status == 400 and "authorized" in message["error"]


def test_offline_workflow_and_otel(server):
    srv, _ = server
    workflow = {"executions": [{"workflow": "sample", "status": "failed", "error": "timeout"}]}
    otel = {"resourceSpans": [{"scopeSpans": [{"spans": [{"status": {"code": 2}}]}]}]}
    for kind, contents in (("workflow", workflow), ("otel", otel)):
        status, data = call(srv, "POST", "/api/analyze",
                            {"kind": kind, "contents": json.dumps(contents)}, json_headers(srv))
        assert status == 201 and data["report"]["events"] == 1


def test_oversized_request_rejected(server):
    srv, _ = server
    assert call(srv, "POST", "/api/demo", headers={"Content-Type": "application/json",
                                                   "Content-Length": "999999999"})[0] == 413


def test_loopback_binding_enforced(tmp_path):
    with pytest.raises(ValueError, match="127.0.0.1"):
        LocalServer(("0.0.0.0", 0), directory=tmp_path)

def test_update_status_and_manual_update_request(server, tmp_path, monkeypatch):
    monkeypatch.setenv("BUGCIRCUIT_DATA_DIR", str(tmp_path / "state" / "reports"))
    from bugcircuit.updater import safe_status, request_path
    srv, _ = server
    safe_status(state="current", commit="abcdef01")
    status, payload = call(srv, "GET", "/api/update-status")
    assert status == 200 and payload["commit"] == "abcdef01"
    status, payload = call(srv, "POST", "/api/updates/check", {}, json_headers(srv))
    assert status == 202 and payload["queued"] is True and request_path().exists()
    status, _ = call(srv, "POST", "/api/updates/check", {}, {"Content-Type": "application/json", "Origin": "https://attacker.test"})
    assert status == 403
