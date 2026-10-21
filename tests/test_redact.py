from bugcircuit.redact import header_summary, safe_text, safe_url


def test_url_discards_credentials_queries_and_fragment():
    value = safe_url("https://admin:pw@example.com/auth/callback?code=abc123&state=secret#fragment")
    assert "admin" not in value
    assert "pw" not in value
    assert "abc123" not in value
    assert "secret" not in value
    assert "fragment" not in value
    assert "code=REDACTED" in value
    assert "state=REDACTED" in value


def test_relative_location_also_redacted():
    assert safe_url("/callback?custom=very-private") == "/callback?custom=REDACTED"


def test_headers_are_allowlisted():
    got = header_summary([{"name": "Authorization", "value": "Bearer sensitive"},
                          {"name": "Set-Cookie", "value": "session=sensitive"},
                          {"name": "Content-Type", "value": "application/json"}])
    assert got == {"content-type": "application/json"}


def test_error_strings_redact_tokens_urls_and_emails():
    value = safe_text("failed https://example.com?custom=private Bearer abc123 user@corp.com")
    assert "private" not in value
    assert "abc123" not in value
    assert "user@corp.com" not in value


def test_malformed_embedded_url_does_not_recurse():
    from bugcircuit.redact import safe_text, safe_url

    assert safe_text("failed link http:///bad") == "failed link http:///bad"
    assert safe_url("http:///bad") == "http:///bad"
    assert "SECRET" not in safe_text("bad http://?token=SECRET")


def test_malformed_url_redacts_fragmented_email():
    from bugcircuit.redact import safe_text

    assert "private@example.com" not in safe_text("http:///private@example.com")
