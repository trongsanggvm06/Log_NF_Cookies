"""Test persisted query with sha256Hash for createAutoLoginToken."""
import sys
import json
import re
import hashlib
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

# Generate sha256Hash from query string
queries = [
    'mutation { createAutoLoginToken(scope: WEB) }',
    'mutation CreateAutoLoginToken { createAutoLoginToken(scope: WEB) }',
    'mutation { createAutoLoginToken }',
    'mutation { createAutoLoginToken(scope: IOS) }',
    'mutation { createAutoLoginToken(scope: AKIRA) }',
    'mutation CreateAutoLoginToken($scope: TokenScope!) { createAutoLoginToken(scope: $scope) }',
]

for query_str in queries:
    hash_val = hashlib.sha256(query_str.encode('utf-8')).hexdigest()
    print(f"\nQuery: {query_str}")
    print(f"  sha256Hash: {hash_val}")

    # Try as persisted query
    payload = {
        "operationName": "createAutoLoginToken",
        "variables": {},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hash_val,
            }
        }
    }
    r = requests.post(
        "https://web.prod.cloud.netflix.com/graphql",
        headers={**headers_web, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
        verify=False,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")

    # Also try with query + variables
    payload2 = {
        "operationName": "createAutoLoginToken",
        "query": query_str,
        "variables": {},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hash_val,
            }
        }
    }
    r2 = requests.post(
        "https://web.prod.cloud.netflix.com/graphql",
        headers={**headers_web, "Content-Type": "application/json"},
        json=payload2,
        timeout=15,
        verify=False,
    )
    print(f"  With query: {r2.status_code} {r2.text[:300]}")
