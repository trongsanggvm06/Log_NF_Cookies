"""Test FINAL: ?error=invalid_token có gây 404 page không."""
import sys
import json
import re
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Test các URL gây error
error_urls = [
    "https://www.netflix.com/?error=invalid_token",
    "https://www.netflix.com/?error=invalid_token&nftoken=BAD",
    "https://www.netflix.com/browse?error=invalid_token",
    "https://www.netflix.com/?nftoken=BAD_TOKEN_HERE",
    "https://www.netflix.com/?nftoken=INVALID",
    "https://www.netflix.com/?nftoken=",
    "https://www.netflix.com/vn-en/?error=invalid_token",
]

for url in error_urls:
    print(f"\n=== {url[:80]} ===")
    session = requests.Session()
    session.verify = False
    try:
        resp = session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            },
            timeout=15,
            allow_redirects=True,
        )
        print(f"  Final URL: {resp.url[:120]}")
        print(f"  Status: {resp.status_code}")
        # Check for NSES-404
        has_nses = "NSES-404" in resp.text or "Lost your way" in resp.text
        has_404 = "404" in resp.text[:5000] or "not found" in resp.text.lower()[:5000]
        has_login = "Sign In" in resp.text or "/login" in resp.url
        has_unsupported = "/unsupported" in resp.url
        print(f"  NSES-404: {has_nses}")
        print(f"  Login: {has_login}")
        print(f"  Unsupported: {has_unsupported}")
    except Exception as e:
        print(f"  ERR: {e}")


# Test critical case: token dung nhung truy cap khong co cookie
print("\n\n=== Critical: Valid token without client cookies ===")
from netflix import _create_token_hybrid, parse_cookies, PC_LOGIN_BASE
with open('cookies_test.json', 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)
parsed = parse_cookies(json.dumps(REAL_COOKIES[0]))
token_data, _ = _create_token_hybrid(parsed)
token = token_data["token"]

session = requests.Session()
session.verify = False
# KHONG set cookies
resp = session.get(
    PC_LOGIN_BASE + token,
    headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) Safari/604.1"},
    timeout=15,
    allow_redirects=True,
)
print(f"  Final: {resp.url[:120]}")
print(f"  NSES-404: {'NSES-404' in resp.text or 'Lost your way' in resp.text}")


# Test với expired token
print("\n\n=== Test: token da su dung (1 lan) ===")
session = requests.Session()
session.cookies.update(parsed)
session.verify = False
url1 = PC_LOGIN_BASE + token
# Lan 1
resp1 = session.get(url1, headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari/604.1"}, timeout=15, allow_redirects=True)
print(f"  Lan 1: {resp1.url[:80]}, NSES-404: {'NSES-404' in resp1.text}")

# Lay cookies moi (cookie da duoc refresh)
new_cookies = dict(session.cookies)
print(f"  Cookies sau lan 1: {list(new_cookies.keys())}")

# Tao session moi (khong co cookies)
session2 = requests.Session()
session2.verify = False
# Test url LAN 2 (cung token)
resp2 = session2.get(url1, headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari/604.1"}, timeout=15, allow_redirects=True)
print(f"  Lan 2 (no cookies, same token): {resp2.url[:80]}")
print(f"  Lan 2 NSES-404: {'NSES-404' in resp2.text or 'Lost your way' in resp2.text}")
print(f"  Lan 2 'error=invalid_token': {'error=invalid_token' in resp2.url}")
