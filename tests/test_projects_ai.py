"""Repository integration, data protection, loopback AI and HTTP tests."""
import http.client
import json
import subprocess
import threading
from pathlib import Path

import pytest

from bugcircuit.analyze import analyze
from bugcircuit.models import Event
from bugcircuit.projects import ProjectStore, audit_project, _public_url
from bugcircuit.web import LocalServer


def create_git_repo(tmp_path):
    repo = tmp_path / "example-code"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "main.py").write_text('import requests\nrequests.get("https://example.org", verify=False)\n')
    (repo / ".env").write_text('SUPER_SECRET_PASSWORD=should_not_leak')
    (repo / "README.md").write_text('# Demo\n')
    (repo / "tests").mkdir()
    (repo / "tests" / "test_example.py").write_text('def test_a(): assert True\n')
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    return repo


def test_private_clone_can_be_connected_by_folder(tmp_path):
    repo = create_git_repo(tmp_path)
    store = ProjectStore(tmp_path / "data")
    item = store.connect_folder(str(repo))
    assert item["origin"] == "local (GitHub Desktop)"
    assert store.connect_folder(str(repo))["id"] == item["id"]
    assert len(store.list()) == 1
    assert not (repo / "__pycache__").exists()
    report = audit_project(item)
    data = json.dumps(report.as_dict())
    assert "REPO_SENSITIVE_FILES_TRACKED" in data
    assert "REPO_TLS_VERIFICATION_DISABLED" in data
    assert "SUPER_SECRET_PASSWORD" not in data
    assert "should_not_leak" not in data
    assert store.forget(item["id"])
    assert repo.exists() and (repo / "main.py").exists()


def test_empty_repos_and_non_git_paths_rejected(tmp_path):
    with pytest.raises(ValueError):
        ProjectStore(tmp_path / "private").connect_folder(str(tmp_path))
    assert not (tmp_path / "private" / "git-projects").exists()


@pytest.mark.parametrize("url", ["https://evil.com/owner/repo", "https://github.com/owner/repo?token=secret", "file:///tmp/test", "https://github.com/owner/../bad", "https://github.com/owner/repo#fragment", "https://github.com@attacker.invalid/owner/repo"])
def test_git_url_validation_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        _public_url(url)


def test_normal_github_urls():
    assert _public_url("https://github.com/acme/a-repo")[1] == "acme/a-repo"
    assert _public_url("https://github.com/acme/a-repo.git")[1] == "acme/a-repo"


def test_git_audit_does_not_follow_symlink(tmp_path):
    repo = create_git_repo(tmp_path)
    outside = tmp_path / "do-not-read.py"
    outside.write_text('password=important_secret_9876\nverify=False\n')
    link = repo / "symlink.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks need privileges on Windows")
    subprocess.run(["git", "-C", str(repo), "add", "symlink.py"], check=True)
    item = ProjectStore(tmp_path / "data").connect_folder(str(repo))
    result = json.dumps(audit_project(item).as_dict())
    assert "important_secret_9876" not in result
    assert "symlink.py" not in result


def test_http_403_not_automatic_auth_failure():
    result = analyze([Event(id="E0001", kind="http", status=403, url="https://example.org")], "test")
    codes = [f.code for f in result.findings]
    assert "HTTP_ACCESS_FORBIDDEN" in codes
    assert "HTTP_AUTH_REJECTED" not in codes
    assert "WAF" in result.findings[0].explanation


@pytest.fixture
def web_server(tmp_path):
    srv = LocalServer(("127.0.0.1", 0), directory=tmp_path / "reports")
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    thread.join(timeout=3)


def req(srv, method, route, payload=None, origin=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=8)
    headers = {"Host": f"127.0.0.1:{srv.server_port}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin
    conn.request(method, route, json.dumps(payload) if payload is not None else None, headers)
    response = conn.getresponse()
    body = response.read()
    status = response.status
    conn.close()
    return status, json.loads(body)


def test_project_web_flow(web_server, tmp_path):
    repo = create_git_repo(tmp_path)
    srv = web_server
    valid_origin = f"http://127.0.0.1:{srv.server_port}"
    status, output = req(srv, "POST", "/api/projects/connect", {"mode": "folder", "path": str(repo)}, valid_origin)
    assert status == 201
    project_id = output["project"]["id"]
    assert req(srv, "GET", "/api/projects")[1]["projects"][0]["id"] == project_id
    status, output = req(srv, "POST", f"/api/projects/{project_id}/audit", {}, valid_origin)
    assert status == 201
    report_id = output["report"]["id"]
    status, output = req(srv, "GET", f"/api/reports/{report_id}")
    assert status == 200
    assert output["source"] == "Repository audit: example-code"
    status, output = req(srv, "DELETE", f"/api/projects/{project_id}", {}, valid_origin)
    assert status == 200 and output["files_preserved"] is True
    assert repo.exists()


def test_cross_origin_cannot_connect_folder(web_server, tmp_path):
    repo = create_git_repo(tmp_path)
    srv = web_server
    status, output = req(srv, "POST", "/api/projects/connect",
                         {"mode": "folder", "path": str(repo)}, "https://untrusted.example")
    assert status == 403
    assert req(srv, "GET", "/api/projects")[1]["projects"] == []


def test_ai_models_failure_has_no_cloud_fallback(monkeypatch):
    from bugcircuit import local_ai
    def offline(*args, **kwargs):
        raise ConnectionRefusedError()
    monkeypatch.setattr(local_ai, "urlopen", offline)
    assert local_ai.models() == []
    with pytest.raises(ValueError):
        local_ai.explain({"findings": []}, "nonexistent:1b")


def test_only_explicit_small_ai_model_downloads(monkeypatch):
    from bugcircuit import local_ai
    with pytest.raises(ValueError):
        local_ai.pull_model("arbitrary:70b", lambda _: None)

    class Response:
        def __enter__(self):
            return [b'{"status":"pulling manifest"}\n',
                    b'{"status":"downloading digest","completed":15,"total":30}\n',
                    b'{"status":"success"}\n']
        def __exit__(self, *args):
            pass
    calls = []
    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/pull"
        assert json.loads(request.data)["name"] == "qwen2.5-coder:1.5b"
        return Response()
    monkeypatch.setattr(local_ai, "urlopen", fake_urlopen)
    local_ai.pull_model("qwen2.5-coder:1.5b", calls.append)
    assert calls[-1]["phase"] == "success"
    assert calls[1]["downloaded"] == 15
