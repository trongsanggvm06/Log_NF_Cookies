"""End-to-end test: generate token, then OPEN the URL to verify it doesn't return 404."""
import sys
import json
import re
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from netflix import (
    _create_token_hybrid, _create_token_ios_ftl, _create_token_via_shakti,
    _build_cookie_header, parse_cookies, PC_LOGIN_BASE, MOBILE_LOGIN_BASE,
)

with open('cookies_test.json', 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)

# Test tung cookie
for i, cookie_arr in enumerate(REAL_COOKIES, 1):
    print(f"\n{'='*80}")
    print(f"COOKIE {i}")
    print(f"{'='*80}")

    parsed = parse_cookies(json.dumps(cookie_arr))
    print(f"NetflixId: {bool(parsed.get('NetflixId'))}")

    # Generate token bang hybrid
    token_data, log = _create_token_hybrid(parsed)
    if not token_data or not token_data.get("token"):
        print(f"  [FAIL] khong generate duoc token")
        continue

    token = token_data["token"]
    source = token_data.get("source", "?")
    print(f"  Source: {source}")
    print(f"  Token len: {len(token)}")
    print(f"  Token preview: {token[:60]}...{token[-40:]}")

    # Tao URL
    web_url = PC_LOGIN_BASE + token
    mobile_url = MOBILE_LOGIN_BASE + token
    print(f"  Web URL: {web_url[:100]}...")

    # Test 1: GET web URL (no cookie) → xem Netflix tra ve gi
    print(f"\n  --- Test 1: GET web URL (no client cookie) ---")
    try:
        resp = requests.get(
            web_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            },
            timeout=15,
            verify=False,
            allow_redirects=False,
        )
        print(f"    Status: {resp.status_code}")
        print(f"    Location: {resp.headers.get('Location', '(none)')[:150]}")
        body = resp.text[:500]
        if "NSES-404" in body or "Lost your way" in body:
            print(f"    [NSES-404 DETECTED] body contains 'Lost your way'")
        elif "Sign In" in body or "login" in resp.url:
            print(f"    [OK] redirected to login (token invalid or expired)")
        elif resp.status_code in (301, 302, 303, 307):
            print(f"    [REDIRECT] to: {resp.headers.get('Location', '?')[:200]}")
        else:
            print(f"    [BODY] {body[:200]}")
    except Exception as e:
        print(f"    [ERR] {e}")

    # Test 2: GET with mobile User-Agent (simulate iPhone Safari)
    print(f"\n  --- Test 2: GET with mobile UA (iPhone Safari) ---")
    try:
        resp = requests.get(
            web_url,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            },
            timeout=15,
            verify=False,
            allow_redirects=False,
        )
        print(f"    Status: {resp.status_code}")
        print(f"    Location: {resp.headers.get('Location', '(none)')[:150]}")
        body = resp.text[:500]
        if "NSES-404" in body or "Lost your way" in body:
            print(f"    [NSES-404 DETECTED] body contains 'Lost your way'")
        elif resp.status_code in (301, 302, 303, 307):
            print(f"    [REDIRECT] to: {resp.headers.get('Location', '?')[:200]}")
    except Exception as e:
        print(f"    [ERR] {e}")

    # Test 3: GET /browse?nftoken=... (the path that worked in iOS app)
    browse_url = f"https://www.netflix.com/browse?nftoken={token}"
    print(f"\n  --- Test 3: GET /browse?nftoken=... ---")
    try:
        resp = requests.get(
            browse_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            },
            timeout=15,
            verify=False,
            allow_redirects=False,
        )
        print(f"    Status: {resp.status_code}")
        print(f"    Location: {resp.headers.get('Location', '(none)')[:150]}")
    except Exception as e:
        print(f"    [ERR] {e}")

    # Test 4: GET /unsupported?nftoken=... (Android app link)
    print(f"\n  --- Test 4: GET /unsupported?nftoken=... ---")
    try:
        resp = requests.get(
            mobile_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            },
            timeout=15,
            verify=False,
            allow_redirects=False,
        )
        print(f"    Status: {resp.status_code}")
        print(f"    Location: {resp.headers.get('Location', '(none)')[:150]}")
    except Exception as e:
        print(f"    [ERR] {e}")

    if i >= 2:  # test 2 cookie đầu là đủ
        break
