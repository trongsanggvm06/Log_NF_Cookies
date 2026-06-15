"""Test GraphQL createAutoLoginToken with scope argument."""
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

# Get authURL/buildId
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

# Find what fields are available in createAutoLoginToken
print("\n=== Test 1: Introspection - get fields of createAutoLoginToken ===")
introspect_queries = [
    {
        "query": "query IntrospectionQuery { __type(name: \"createAutoLoginToken\") { name, kind, inputFields { name, type { name, kind } } } }",
        "operationName": "IntrospectionQuery"
    },
    {
        "query": "{ __schema { mutationType { fields { name, args { name, type { name } } } } } }"
    },
]

for q in introspect_queries:
    print(f"\n  Query: {json.dumps(q)[:150]}")
    r = requests.post(
        "https://web.prod.cloud.netflix.com/graphql",
        headers={**headers_web, "Content-Type": "application/json"},
        json=q,
        timeout=15,
        verify=False,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:1500]}")


# Test 2: createAutoLoginToken with various scope values
print("\n\n=== Test 2: createAutoLoginToken with various scopes ===")
scopes = ["WEB", "IOS", "ANDROID", "MOBILE", "BROWSER", "ANY", "DEFAULT", "AKIRA"]
for scope in scopes:
    q = {
        "query": f'mutation {{ createAutoLoginToken(scope: "{scope}") {{ token, expires }} }}',
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
    if "errors" in body and "token" not in body:
        err = json.loads(body).get("errors", [{}])[0].get("message", "")
        print(f"  scope={scope:10s} -> {r.status_code} ERR: {err[:150]}")
    else:
        print(f"  scope={scope:10s} -> {r.status_code} BODY: {body[:200]}")


# Test 3: With authURL in input
print("\n\n=== Test 3: createAutoLoginToken with authURL input ===")
# Mutation with input object
input_formats = [
    {"input": {"scope": "WEB", "authURL": auth_url}},
    {"authURL": auth_url, "scope": "WEB"},
    {"scope": "WEB"},
    {},
]

for inp in input_formats:
    print(f"\n  Input: {json.dumps(inp)[:200]}")
    # Inline query with input
    q = {
        "query": f'mutation($input: createAutoLoginTokenInput!) {{ createAutoLoginToken(input: $input) {{ token, expires }} }}',
        "operationName": "createAutoLoginToken",
        "variables": {"input": inp},
    }
    r = requests.post(
        "https://web.prod.cloud.netflix.com/graphql",
        headers={**headers_web, "Content-Type": "application/json"},
        json=q,
        timeout=15,
        verify=False,
    )
    body = r.text
    print(f"  Status: {r.status_code}, body: {body[:300]}")


# Test 4: With authURL as top-level argument
print("\n\n=== Test 4: createAutoLoginToken with top-level authURL ===")
q = {
    "query": f'mutation {{ createAutoLoginToken(scope: "WEB", authURL: "{auth_url}") {{ token, expires }} }}',
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
