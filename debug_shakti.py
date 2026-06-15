"""Debug script - test Shakti pathEvaluator step by step."""
import sys
import json
import re
import urllib.parse
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from netflix import _build_cookie_header, parse_cookies, SHAKTI_BUILD_IDS

REAL_COOKIES_PATH = sys.argv[1] if len(sys.argv) > 1 else None
if not REAL_COOKIES_PATH:
    print("Usage: python debug_shakti.py <path-to-json-file>")
    sys.exit(1)

with open(REAL_COOKIES_PATH, 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)
if not REAL_COOKIES:
    print("Empty cookie file")
    sys.exit(1)

# Lay cookie 1
cookie_arr = REAL_COOKIES[0] if isinstance(REAL_COOKIES, list) and isinstance(REAL_COOKIES[0], list) else REAL_COOKIES
raw = json.dumps(cookie_arr)
parsed = parse_cookies(raw)
cookie_header = _build_cookie_header(parsed)

print("=" * 80)
print("DEBUG 1: Test multiple buildIds with proper headers")
print("=" * 80)

# Headers giong Netflix web
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

# Step 1: GET www.netflix.com de lay authURL va buildId
print("\n--- Step 1: GET https://www.netflix.com/ ---")
try:
    resp = requests.get(
        "https://www.netflix.com/",
        headers=headers_web,
        timeout=20,
        verify=False,
        allow_redirects=True,
    )
    print(f"  Status: {resp.status_code}")
    print(f"  URL final: {resp.url}")
    print(f"  HTML size: {len(resp.text)} chars")
    print(f"  Cookies set: {list(resp.cookies.keys())}")
    # Update cookie header voi cookies moi set
    for k, v in resp.cookies.items():
        if k not in parsed or not parsed.get(k):
            parsed[k] = v
    cookie_header2 = _build_cookie_header(parsed)
    headers_web["Cookie"] = cookie_header2

    # Find authURL trong HTML
    auth_url = None
    build_id = None
    m = re.search(r'"authURL"\s*:\s*"([^"]+)"', resp.text or "")
    if m:
        auth_url = m.group(1)
        print(f"  [OK] authURL found: {auth_url[:60]}...")
    else:
        # Try other patterns
        patterns = [
            r'authURL["\s\\:]+([^",}\s]+)',
            r'"authURL":"([^"]+)"',
            r'authURL=([^&"]+)',
        ]
        for pat in patterns:
            m = re.search(pat, resp.text or "")
            if m:
                auth_url = m.group(1)
                print(f"  [OK] authURL found (alt pattern): {auth_url[:60]}...")
                break

    if not auth_url:
        print(f"  [WARN] authURL not found in page")
        print(f"  Page head: {resp.text[:500]}")
        sys.exit(1)

    # Find buildId
    patterns = [
        r'"BUILD_IDENTIFIER"\s*:\s*"([^"]+)"',
        r'BUILD_IDENTIFIER["\s\\:]+["\']([^"\']+)["\']',
        r'"buildId"\s*:\s*"([^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, resp.text or "")
        if m:
            build_id = m.group(1)
            print(f"  [OK] buildId from page: {build_id}")
            break
    if not build_id:
        print(f"  [WARN] buildId not in page, will try hardcoded list")

except Exception as e:
    print(f"  [ERR] {type(e).__name__}: {e}")
    sys.exit(1)


# Step 2: POST pathEvaluator
print("\n--- Step 2: POST pathEvaluator ---")
test_build_ids = [build_id] if build_id else SHAKTI_BUILD_IDS
test_build_ids = [b for b in test_build_ids if b]  # Remove None

for bid in test_build_ids[:3]:  # test 3
    url = f"https://www.netflix.com/api/shakti/{bid}/pathEvaluator"
    try:
        paths = [["createAutoLoginToken"]]
        body_data = {
            "paths": paths,
            "authURL": auth_url,
        }
        body_str = "path=" + urllib.parse.quote(
            json.dumps(paths, separators=(",", ":")),
            safe="",
        ) + "&authURL=" + urllib.parse.quote(auth_url, safe="")

        print(f"\n  BuildId: {bid}")
        print(f"  URL: {url}")
        print(f"  Body: {body_str[:200]}...")

        resp = requests.post(
            url,
            headers={
                **headers_web,
                "Content-Type": "application/x-www-form-urlencoded",
                "x-netflix.context.flavor": "akira",
            },
            data=body_str,
            timeout=20,
            verify=False,
        )
        print(f"  Status: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('Content-Type', '?')}")
        print(f"  Response (first 500): {resp.text[:500]}")

        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"  JSON keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                if isinstance(data, dict):
                    jg = data.get("jsonGraph") or data
                    print(f"  jsonGraph keys: {list(jg.keys()) if isinstance(jg, dict) else 'not dict'}")
                    if "createAutoLoginToken" in jg:
                        print(f"  createAutoLoginToken value: {str(jg['createAutoLoginToken'])[:200]}")
            except Exception as e:
                print(f"  JSON parse err: {e}")
    except Exception as e:
        print(f"  [ERR] {type(e).__name__}: {e}")


# Step 3: Try GraphQL endpoint
print("\n" + "=" * 80)
print("DEBUG 2: Try GraphQL endpoint (web.prod.cloud.netflix.com/graphql)")
print("=" * 80)

# Need persisted query for createAutoLoginToken. Search community-known IDs
# The actual operation may be under different name. Test membership status first as smoke test.
graphql_urls = [
    "https://web.prod.cloud.netflix.com/graphql",
    "https://www.netflix.com/graphql",
]
for gql_url in graphql_urls:
    print(f"\n  Testing {gql_url}")
    try:
        # Test basic query
        body = {
            "query": "query { __typename }",
            "operationName": "Ping",
        }
        resp = requests.post(
            gql_url,
            headers={
                **headers_web,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=10,
            verify=False,
        )
        print(f"  Ping: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"  [ERR] {e}")


# Step 4: Try memberapi pathEvaluator (the actual real endpoint per gist)
print("\n" + "=" * 80)
print("DEBUG 3: Try memberapi pathEvaluator (/nq/website/memberapi/release/)")
print("=" * 80)
try:
    url = "https://www.netflix.com/nq/website/memberapi/release/pathEvaluator"
    paths = [["createAutoLoginToken"]]
    body_str = "path=" + urllib.parse.quote(
        json.dumps(paths, separators=(",", ":")),
        safe="",
    ) + "&authURL=" + urllib.parse.quote(auth_url, safe="")
    print(f"  URL: {url}")
    print(f"  Body: {body_str[:200]}...")
    resp = requests.post(
        url,
        headers={
            **headers_web,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body_str,
        timeout=20,
        verify=False,
    )
    print(f"  Status: {resp.status_code}")
    print(f"  Response (first 500): {resp.text[:500]}")
except Exception as e:
    print(f"  [ERR] {type(e).__name__}: {e}")
