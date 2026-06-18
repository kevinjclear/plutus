import base64

from plutus.fetch_simplefin import parse_access_url, _accounts_request


def test_parse_access_url_splits_creds_and_base():
    base, user, pw = parse_access_url("https://abc123:secretpw@bridge.simplefin.org/simplefin")
    assert base == "https://bridge.simplefin.org/simplefin"
    assert user == "abc123" and pw == "secretpw"


def test_parse_access_url_without_creds():
    base, user, pw = parse_access_url("https://bridge.simplefin.org/simplefin")
    assert base == "https://bridge.simplefin.org/simplefin"
    assert user == "" and pw == ""


def test_accounts_request_has_browser_ua_and_auth():
    req = _accounts_request("https://abc123:secretpw@beta-bridge.simplefin.org/simplefin")
    # endpoint is <base>/accounts with no double slash
    assert req.full_url == "https://beta-bridge.simplefin.org/simplefin/accounts"
    # browser-like UA to get past Cloudflare 1010 (the default Python UA is blocked)
    ua = req.get_header("User-agent")
    assert ua and "Mozilla/5.0" in ua and "Python-urllib" not in ua
    # Basic auth built from the embedded credentials
    expected = "Basic " + base64.b64encode(b"abc123:secretpw").decode()
    assert req.get_header("Authorization") == expected


def test_accounts_request_trailing_slash_no_double():
    req = _accounts_request("https://u:p@beta-bridge.simplefin.org/simplefin/")
    assert req.full_url == "https://beta-bridge.simplefin.org/simplefin/accounts"
