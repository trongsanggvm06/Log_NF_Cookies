"""Test scenario: iOS Universal Link scenario - app claims URL."""
import sys
import json
import re
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Mo phong iOS Universal Link flow:
# User bam link tu Telegram/Message, iOS check UL:
# - Domain: netflix.com → Netflix app claims
# - AASA: path '/' khong bi exclude → mo Netflix app
# - Netflix app nhan URL qua UL, can parse nftoken
# - Netflix app goi FTL API de redeem token
# - Neu token KO phai FTL format → fail → app fallback
# - App mo Safari voi URL goc → user thay 404

# De test: goi iOS FTL API voi token vua tao de verify app co the parse/redeem
import sys
sys.path.insert(0, '.')
from netflix import _create_token_hybrid, parse_cookies, NFTOKEN_API_URL, NFTOKEN_HEADERS, NFTOKEN_QUERY_PARAMS

with open('cookies_test.json', 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)

parsed = parse_cookies(json.dumps(REAL_COOKIES[0]))

# Lay token tu iOS FTL
token_data, log = _create_token_hybrid(parsed)
token = token_data["token"]
print(f"Token: {token[:80]}...")
print(f"Source: {token_data.get('source')}")

# Test: Netflix iOS app se goi endpoint nao voi token nay?
# Theo reverse engineering, Netflix app goi:
# 1. account/verify (verify token)
# 2. login (use token to login)
# Endpoint co the la: https://ios.prod.ftl.netflix.com/iosui/login

# Test verify endpoint
print("\n=== Test verify endpoint ===")
verify_urls = [
    "https://ios.prod.ftl.netflix.com/iosui/account/verify",
    "https://ios.prod.ftl.netflix.com/iosui/login",
    "https://ios.prod.ftl.netflix.com/iosui/loginWithToken",
    f"https://ios.prod.ftl.netflix.com/iosui/user/15.48?path=%5B%22account%22%2C%22verify%22%2C%22default%22%5D",
]

for url in verify_urls:
    try:
        session = requests.Session()
        session.cookies.update(parsed)
        session.verify = False

        resp = session.get(
            url,
            headers=NFTOKEN_HEADERS,
            timeout=15,
        )
        print(f"\n  URL: {url[:80]}...")
        print(f"  Status: {resp.status_code}")
        print(f"  Body: {resp.text[:200]}")
    except Exception as e:
        print(f"  ERR: {e}")


# Test: User comment tren Telegram thuong gap 404 khi:
# 1. Click vao link trong Telegram (iOS Safari / Telegram browser)
# 2. iOS UL claim → open Netflix app
# 3. Netflix app process nftoken → ???
# 4. Neu app fail → back to browser → 404

# De kiem tra: Netflix app process token theo cach nao?
# Reverse: app goi POST toi /iosui/login voi token
print("\n\n=== Test: POST iosui/login with token ===")
login_url = "https://ios.prod.ftl.netflix.com/iosui/login"
login_body = {
    "token": token,
    "esn": NFTOKEN_QUERY_PARAMS["esn"],
    "appVersion": NFTOKEN_QUERY_PARAMS["appVersion"],
}

session = requests.Session()
session.cookies.update(parsed)
session.verify = False

try:
    resp = session.post(
        login_url,
        headers={**NFTOKEN_HEADERS, "Content-Type": "application/json"},
        json=login_body,
        timeout=15,
    )
    print(f"  Status: {resp.status_code}")
    print(f"  Body: {resp.text[:500]}")
except Exception as e:
    print(f"  ERR: {e}")


# Test the "fallback" path that Netflix iOS app uses for nftoken links
# Neu app process token fail, no se redirect ve URL goc voi error param
print("\n\n=== Test: Simulate iOS app fallback to Safari ===")
# iOS app fallback thuong redirect: netflix.com/?nftoken=XXX&error=invalid_token
# Hoặc: netflix.com/clearcookies?action=signout
fallback_urls = [
    f"https://www.netflix.com/?nftoken={token}&error=invalid_token",
    f"https://www.netflix.com/clearcookies?nftoken={token}",
    f"https://www.netflix.com/?error=invalid_token",
]
for url in fallback_urls:
    try:
        session = requests.Session()
        session.verify = False
        resp = session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) Safari/604.1"},
            timeout=15,
            allow_redirects=True,
        )
        print(f"  URL: {url[:80]}...")
        print(f"  Final: {resp.url[:120]}, status={resp.status_code}")
        if "NSES-404" in resp.text:
            print(f"    [NSES-404 DETECTED]")
    except Exception as e:
        print(f"  ERR: {e}")


# Critical test: what URL does Netflix iOS app show when click on nftoken link
# and it cannot redeem the token?
# We need to capture this from actual iOS device, but we can guess
# Common pattern: netflix:// or netflix.app.link
print("\n\n=== Test: Custom URL schemes (netflix://) ===")
custom_urls = [
    f"netflix://www.netflix.com/?nftoken={token}",
    f"nflxext://www.netflix.com/?nftoken={token}",
    f"https://app.link/netflix?nftoken={token}",
]
for url in custom_urls:
    try:
        session = requests.Session()
        session.verify = False
        resp = session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) Safari/604.1"},
            timeout=10,
            allow_redirects=False,
        )
        print(f"  {url[:60]}... -> {resp.status_code} {resp.headers.get('Location', '')[:80]}")
    except Exception as e:
        print(f"  ERR: {e}")
