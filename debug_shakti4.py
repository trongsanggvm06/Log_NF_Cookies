"""Test createAutoLoginToken as leaf String (returns token directly)."""
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
auth_url = None
m = re.search(r'"authURL"\s*:\s*"([^"]+)"', resp.text or "")
if m:
    auth_url = m.group(1)
print(f"authURL: {auth_url[:60] if auth_url else 'NONE'}")

# Test 1: Just `createAutoLoginToken(scope: "X")` - returns String directly
print("\n=== Test 1: createAutoLoginToken returns String directly ===")
scopes = ["WEB", "IOS", "ANDROID", "MOBILE", "BROWSER", "DEFAULT", "AKIRA", "WEB_CLIENT"]
for scope in scopes:
    q = {
        "query": f'mutation {{ createAutoLoginToken(scope: "{scope}") }}',
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
    if "errors" in body:
        try:
            err = json.loads(body).get("errors", [{}])[0].get("message", "")
            # Truncate any embedded token
            err_short = err[:200]
        except:
            err_short = body[:200]
        print(f"  scope={scope:12s} -> {r.status_code} ERR: {err_short}")
    else:
        print(f"  scope={scope:12s} -> {r.status_code} BODY: {body[:300]}")


# Test 2: If errors persist, try without scope to see full schema requirement
print("\n=== Test 2: Try with no args to discover all required args ===")
q = {
    "query": 'mutation { createAutoLoginToken }',
    "operationName": "createAutoLoginToken",
}
r = requests.post(
    "https://web.prod.cloud.netflix.com/graphql",
    headers={**headers_web, "Content-Type": "application/json"},
    json=q,
    timeout=15,
    verify=False,
)
print(f"  Status: {r.status_code}, body: {r.text[:500]}")


# Test 3: Try with authURL in headers (some Netflix endpoints use this pattern)
print("\n=== Test 3: Send authURL as header ===")
q = {
    "query": 'mutation { createAutoLoginToken(scope: "WEB") }',
    "operationName": "createAutoLoginToken",
}
r = requests.post(
    "https://web.prod.cloud.netflix.com/graphql",
    headers={
        **headers_web,
        "Content-Type": "application/json",
        "x-netflix.request.client.context": json.dumps({"authURL": auth_url, "appState": "foreground"}),
    },
    json=q,
    timeout=15,
    verify=False,
)
print(f"  Status: {r.status_code}, body: {r.text[:500]}")


# Test 4: Get all mutation fields using __schema with proper auth
print("\n=== Test 4: Full schema introspection with auth ===")
q = {"query": "{ __schema { queryType { name } mutationType { fields { name args { name type { name kind ofType { name kind } } } } } } }"}
r = requests.post(
    "https://web.prod.cloud.netflix.com/graphql",
    headers={**headers_web, "Content-Type": "application/json"},
    json=q,
    timeout=15,
    verify=False,
)
print(f"  Status: {r.status_code}, body: {r.text[:1500]}")
