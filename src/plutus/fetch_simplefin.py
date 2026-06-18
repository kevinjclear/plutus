"""Read-only SimpleFIN fetcher: GET <access-url>/accounts and archive the raw JSON.

The access URL (a secret) is passed in by the caller from env SIMPLEFIN_ACCESS_URL —
never hardcoded or logged."""
from __future__ import annotations

import base64
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

# SimpleFIN Bridge sits behind Cloudflare, which blocks the default Python
# User-Agent with "error code: 1010". Present a browser-like UA so requests pass.
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def parse_access_url(access_url: str) -> tuple[str, str, str]:
    parts = urlsplit(access_url)
    user = parts.username or ""
    password = parts.password or ""
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    base = urlunsplit((parts.scheme, host, parts.path, "", ""))
    return base, user, password


def _accounts_request(access_url: str) -> urllib.request.Request:
    """Build the read-only GET <base>/accounts request with auth + browser UA."""
    base, user, password = parse_access_url(access_url)
    req = urllib.request.Request(f"{base.rstrip('/')}/accounts")
    req.add_header("User-Agent", _USER_AGENT)
    if user or password:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    return req


def fetch_accounts_json(access_url: str, out_path: str) -> str:
    req = _accounts_request(access_url)
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (https only, trusted)
        data = resp.read()
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return out_path
