"""Regression tests for explicit loopback Ollama connection configuration."""
import http.client
import json
import threading

import pytest

from bugcircuit import local_ai
from bugcircuit.web import LocalServer


@pytest.fixture
def server(tmp_path):
    srv = LocalServer(("127.0.0.1", 0), directory=tmp_path / "reports")
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    thread.join(timeout=3)


def request(srv, method, path, payload=None, origin=None):
    connection = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=4)
    headers = {"Content-Type": "application/json", "Host": f"127.0.0.1:{srv.server_port}"}
    if origin:
        headers["Origin"] = origin
    connection.request(method, path, json.dumps(payload) if payload is not None else None, headers)
    response = connection.getresponse()
    status, raw = response.status, response.read()
    connection.close()
    return status, json.loads(raw)


def test_ollama_port_is_loopback_only():
    assert local_ai.host(11435) == "http://127.0.0.1:11435"
    for bad in (0, 80, 65536, True, "127.0.0.1:11435", "https://example.com"):
        with pytest.raises(ValueError):
            local_ai.host(bad)


def test_ai_port_is_persistent_and_restricted(server, monkeypatch):
    monkeypatch.setattr("bugcircuit.web.ollama_models", lambda port: ["model:1b"] if port == 11435 else [])
    srv = server
    good_origin = f"http://127.0.0.1:{srv.server_port}"
    status, result = request(srv, "POST", "/api/ai/settings", {"port": 11435}, good_origin)
    assert status == 200 and result["endpoint"] == "http://127.0.0.1:11435"
    status, result = request(srv, "GET", "/api/ai/models")
    assert status == 200 and result["models"] == ["model:1b"]
    assert (srv.reports_dir.parent / "local-ai.json").is_file()
    assert LocalServer(("127.0.0.1", 0), directory=srv.reports_dir).ai_port == 11435
    status, _ = request(srv, "POST", "/api/ai/settings", {"port": 11434}, "https://evil.example")
    assert status == 403 and srv.ai_port == 11435
    for bad in ("1234", 80, 65536, True):
        status, _ = request(srv, "POST", "/api/ai/settings", {"port": bad}, good_origin)
        assert status == 400 and srv.ai_port == 11435
