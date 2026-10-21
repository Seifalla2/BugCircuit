import httpx
import pytest

from bugcircuit.probe import ScopeError, inspect_url, validate_target


def test_private_target_requires_opt_in():
    with pytest.raises(ScopeError):
        validate_target("http://127.0.0.1:54321/", {"127.0.0.1"})
    validate_target("http://127.0.0.1:54321/", {"127.0.0.1"}, allow_private=True)


def test_credentials_not_allowed():
    with pytest.raises(ScopeError):
        validate_target("https://me:password@example.com/", {"example.com"})


def test_redirect_out_of_scope_is_not_followed():
    requested = []

    def handler(req):
        requested.append(str(req.url))
        return httpx.Response(302, headers={"Location": "http://blocked.example/next?secret=private"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        events, warnings = inspect_url("http://127.0.0.1:31337/", allow_private=True, client=c)
    assert len(events) == 1
    assert len(requested) == 1
    assert events[0].location.endswith("secret=REDACTED")
    assert any("not followed" in w for w in warnings)


def test_http_server_error_from_mock_transport():
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as c:
        events, _ = inspect_url("http://127.0.0.1:31337/", allow_private=True, client=c)
    assert events[0].status == 503
