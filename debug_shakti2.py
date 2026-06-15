"""Test GraphQL operations for createAutoLoginToken."""
import sys
import json
import re
import urllib.parse
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

# First GET netflix to get authURL, buildId, etc.
print("=== Step 1: GET www.netflix.com ===")
headers_web = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*",
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
print(f"  Status: {resp.status_code}, redirected to: {resp.url}")

# Update cookies
for k, v in resp.cookies.items():
    if k not in parsed or not parsed.get(k):
        parsed[k] = v
headers_web["Cookie"] = _build_cookie_header(parsed)

# extract authURL and buildId
auth_url = None
m = re.search(r'"authURL"\s*:\s*"([^"]+)"', resp.text or "")
if m:
    auth_url = m.group(1)
build_id = None
m = re.search(r'"BUILD_IDENTIFIER"\s*:\s*"([^"]+)"', resp.text or "")
if m:
    build_id = m.group(1)
print(f"  authURL: {auth_url[:60] if auth_url else 'NONE'}")
print(f"  buildId: {build_id}")

# Step 2: Try GraphQL createAutoLoginToken
print("\n=== Step 2: Test GraphQL createAutoLoginToken ===")

# Try as mutation with inline query
queries_to_try = [
    # Inline query (not persisted)
    {
        "query": "mutation { createAutoLoginToken { token, expires } }",
        "operationName": "createAutoLoginToken",
    },
    # Persisted query pattern
    {
        "operationName": "createAutoLoginToken",
        "extensions": {
            "persistedQuery": {
                "id": "createAutoLoginToken",
                "version": 1
            }
        }
    },
    # Path-style (Falcor compat)
    {
        "query": "query { jsonGraph { createAutoLoginToken { token expires } } }",
    },
]

for q in queries_to_try:
    print(f"\n  Trying: {json.dumps(q)[:200]}")
    for gql_url in ["https://web.prod.cloud.netflix.com/graphql"]:
        try:
            r = requests.post(
                gql_url,
                headers={**headers_web, "Content-Type": "application/json"},
                json=q,
                timeout=15,
                verify=False,
            )
            print(f"    {gql_url} -> {r.status_code}")
            print(f"    body: {r.text[:300]}")
        except Exception as e:
            print(f"    ERR: {e}")


# Step 3: Use the right Shakti pathEvaluator buildId
print("\n=== Step 3: Use correct buildId in Shakti ===")
if build_id and auth_url:
    url = f"https://www.netflix.com/api/shakti/{build_id}/pathEvaluator"
    paths = [["createAutoLoginToken"]]
    body_str = "path=" + urllib.parse.quote(
        json.dumps(paths, separators=(",", ":")),
        safe="",
    ) + "&authURL=" + urllib.parse.quote(auth_url, safe="")

    print(f"  URL: {url}")
    r = requests.post(
        url,
        headers={
            **headers_web,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body_str,
        timeout=20,
        verify=False,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Headers: {dict(r.headers)}")
    print(f"  Body: {r.text[:500]}")


# Step 4: Try with x-netflix.request.routing header
print("\n=== Step 4: Try with x-netflix.request.routing header ===")
if build_id and auth_url:
    url = f"https://www.netflix.com/api/shakti/{build_id}/pathEvaluator"
    paths = [["createAutoLoginToken"]]
    body_str = "path=" + urllib.parse.quote(
        json.dumps(paths, separators=(",", ":")),
        safe="",
    ) + "&authURL=" + urllib.parse.quote(auth_url, safe="")

    print(f"  URL: {url}")
    r = requests.post(
        url,
        headers={
            **headers_web,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-netflix.context.flavor": "akira",
            "x-netflix.request.routing": json.dumps({
                "path": f"/shakti/{build_id}/pathEvaluator",
                "control_tag": "website_akira"
            }),
        },
        data=body_str,
        timeout=20,
        verify=False,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")


# Step 5: Try with falcor_server query param
print("\n=== Step 5: Try with falcor_server query param ===")
if build_id and auth_url:
    url = f"https://www.netflix.com/api/shakti/{build_id}/pathEvaluator?falcor_server=0.1.0&withSize=true&materialize=true"
    paths = [["createAutoLoginToken"]]
    body_str = "path=" + urllib.parse.quote(
        json.dumps(paths, separators=(",", ":")),
        safe="",
    ) + "&authURL=" + urllib.parse.quote(auth_url, safe="")

    print(f"  URL: {url}")
    r = requests.post(
        url,
        headers={
            **headers_web,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body_str,
        timeout=20,
        verify=False,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")


# Step 6: Direct createAutoLoginToken with buildId
print("\n=== Step 6: Direct createAutoLoginToken endpoint with buildId ===")
if build_id and auth_url:
    for ep in [
        f"https://www.netflix.com/api/shakti/{build_id}/createAutoLoginToken",
        f"https://www.netflix.com/api/shakti/{build_id}/loginWithToken",
    ]:
        try:
            r = requests.post(
                ep,
                headers={
                    **headers_web,
                    "Content-Type": "application/json",
                },
                json={"authURL": auth_url},
                timeout=15,
                verify=False,
            )
            print(f"  {ep} -> {r.status_code}: {r.text[:300]}")
        except Exception as e:
            print(f"  ERR: {e}")
