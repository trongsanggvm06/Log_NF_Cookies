"""Test FULL follow-redirect flow to see if user actually gets logged in."""
import sys
import json
import re
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from netflix import (
    _create_token_hybrid, _build_cookie_header, parse_cookies,
    PC_LOGIN_BASE, MOBILE_LOGIN_BASE,
)

with open('cookies_test.json', 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)

cookie_arr = REAL_COOKIES[0]
parsed = parse_cookies(json.dumps(cookie_arr))

token_data, log = _create_token_hybrid(parsed)
token = token_data["token"]
source = token_data.get("source", "?")

print(f"Source: {source}, Token len: {len(token)}")
print(f"Token: {token[:60]}...{token[-40:]}")

# Test full flow with redirects
print("\n=== Test FULL redirect flow (mobile Safari UA) ===")
session = requests.Session()
session.verify = False
web_url = PC_LOGIN_BASE + token

try:
    resp = session.get(
        web_url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=20,
        allow_redirects=True,
    )
    print(f"Final URL: {resp.url}")
    print(f"Final status: {resp.status_code}")
    print(f"Cookies set: {list(session.cookies.keys())}")
    print(f"Content length: {len(resp.text)}")
    # Check final page
    if "NSES-404" in resp.text or "Lost your way" in resp.text:
        print(f"  [NSES-404] final page shows error")
    elif "browse" in resp.url and "login" not in resp.url:
        print(f"  [OK] redirected to /browse - token redeemed!")
    elif "login" in resp.url or "Sign In" in resp.text:
        print(f"  [FAIL] redirected to login (token rejected)")
    else:
        print(f"  [?] unknown: {resp.url}")
    # Print relevant HTML signals
    print(f"\n  Page signals:")
    print(f"    contains 'NSES-404': {'NSES-404' in resp.text}")
    print(f"    contains 'Lost your way': {'Lost your way' in resp.text}")
    print(f"    contains 'pageLoadError': {'pageLoadError' in resp.text}")
    print(f"    contains 'browse': {'/browse' in resp.text}")
    print(f"    contains 'login': {'login' in resp.text}")
    print(f"    contains 'profile': {'profile' in resp.text}")
except Exception as e:
    print(f"  [ERR] {e}")


# Test với cookie day du (bao gồm NetflixId + authURL set trong flow)
print("\n\n=== Test 2: With FULL cookie + redirect ===")
session2 = requests.Session()
session2.verify = False
# Update cookie
for k, v in [
    ("NetflixId", parsed.get("NetflixId", "")),
    ("SecureNetflixId", parsed.get("SecureNetflixId", "")),
    ("nfvdid", parsed.get("nfvdid", "")),
]:
    if v:
        session2.cookies.set(k, v, domain=".netflix.com")

try:
    resp = session2.get(
        web_url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        },
        timeout=20,
        allow_redirects=True,
    )
    print(f"Final URL: {resp.url}")
    print(f"Final status: {resp.status_code}")
    print(f"Content length: {len(resp.text)}")
    if "NSES-404" in resp.text or "Lost your way" in resp.text:
        print(f"  [NSES-404]")
    elif "browse" in resp.url and "login" not in resp.url:
        print(f"  [OK] /browse - token redeemed")
    elif "login" in resp.url:
        print(f"  [FAIL] login")
    else:
        print(f"  [?] {resp.url}")
except Exception as e:
    print(f"  [ERR] {e}")
