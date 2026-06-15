"""Test TokenScope enum values."""
import sys
import json
import re
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from netflix import _build_cookie_header, parse_cookies

with open('cookies_test.json', 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)
cookie_arr = REAL_COOKIES[0]
parsed = parse_cookies(json.dumps(cookie_arr))
cookie_header = _build_cookie_header(parsed)

headers_web = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.8",
    "Cookie": cookie_header,
    "x-netflix.esn": "NFCDCH-MC-WEB-1-PXH-NFRSV-NFENF-NFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNF",
    "x-netflix.request.client.type": "akira",
    "x-netflix.context.ui-flavor": "akira",
    "x-netflix.client.appversion": "1.0.0",
}

resp = requests.get(
    "https://www.netflix.com/",
    headers=headers_web,
    timeout=20,
    verify=False,
    allow_redirects=True,
)
for k, v in resp.cookies.items():
    if k not in parsed or not parsed.get(k):
        parsed[k] = v
headers_web["Cookie"] = _build_cookie_header(parsed)

# Test with enum (no quotes) - common TokenScope enum names
print("=== Test: TokenScope as enum (no quotes) ===")
enum_values = [
    "WEB", "IOS", "ANDROID", "MOBILE", "BROWSER", "DEFAULT",
    "AKIRA", "WEB_CLIENT", "TV", "CONSOLE",
    "DESKTOP", "PHONE", "TABLET", "USER",
    "APP", "WEB_APP", "MOBILE_APP",
    "AKIRA_WEB", "CHROME", "SAFARI",
    "MOBILE_BROWSER", "DESKTOP_BROWSER",
]
for scope in enum_values:
    q = {
        "query": f'mutation {{ createAutoLoginToken(scope: {scope}) }}',
        "operationName": "createAutoLoginToken",
    }
    r = requests.post(
        "https://web.prod.cloud.netflix.com/graphql",
        headers={**headers_web, "Content-Type": "application/json"},
        json=q,
        timeout=15,
        verify=False,
    )
    body = r.text
    try:
        j = json.loads(body)
    except:
        j = {}
    errs = j.get("errors", [])
    data = j.get("data", {})
    token = data.get("createAutoLoginToken") if data else None

    if token and isinstance(token, str) and len(token) > 50:
        print(f"  scope={scope:20s} -> 200 TOKEN len={len(token)}")
        print(f"    token preview: {token[:100]}...")
    else:
        err_msg = errs[0].get("message", "")[:120] if errs else "(no errors)"
        print(f"  scope={scope:20s} -> {r.status_code} {err_msg}")


# Also try as ENUM_TYPE introspection
print("\n=== Test: Introspect TokenScope enum ===")
q = {"query": '{ __type(name: "TokenScope") { enumValues { name } } }'}
r = requests.post(
    "https://web.prod.cloud.netflix.com/graphql",
    headers={**headers_web, "Content-Type": "application/json"},
    json=q,
    timeout=15,
    verify=False,
)
print(f"  Status: {r.status_code}, body: {r.text[:500]}")
