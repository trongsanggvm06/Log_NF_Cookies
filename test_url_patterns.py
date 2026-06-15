"""Test thử: mo /browse?nftoken=... thay vi /.nftoken=..."""
import sys
import json
import re
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from netflix import _create_token_hybrid, parse_cookies

with open('cookies_test.json', 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)

parsed = parse_cookies(json.dumps(REAL_COOKIES[0]))
token_data, _ = _create_token_hybrid(parsed)
token = token_data["token"]

# Test cac URL pattern khac nhau
test_urls = [
    ("/  (root)", f"https://www.netflix.com/?nftoken={token}"),
    ("/browse", f"https://www.netflix.com/browse?nftoken={token}"),
    ("/unsupported", f"https://www.netflix.com/unsupported?nftoken={token}"),
    ("/WiHome (legacy)", f"https://www.netflix.com/WiHome?nftoken={token}"),
    ("/Login (login page)", f"https://www.netflix.com/Login?nftoken={token}"),
]

for name, url in test_urls:
    print(f"\n=== {name} ===")
    print(f"  URL: {url[:100]}...")
    session = requests.Session()
    session.verify = False
    for k, v in parsed.items():
        if v:
            session.cookies.set(k, v, domain=".netflix.com")
    try:
        resp = session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            },
            timeout=20,
            allow_redirects=True,
        )
        print(f"  Final URL: {resp.url[:120]}")
        print(f"  Status: {resp.status_code}")
        # Check signals
        has_404 = "NSES-404" in resp.text or "Lost your way" in resp.text
        has_login = "Sign In" in resp.text or "/login" in resp.url
        has_browse = "/browse" in resp.url and "/login" not in resp.url
        has_unsupported = "/unsupported" in resp.url
        has_home = resp.url.rstrip("/") == "https://www.netflix.com"
        print(f"  NSES-404: {has_404}")
        print(f"  Login page: {has_login}")
        print(f"  Browse page: {has_browse}")
        print(f"  Unsupported: {has_unsupported}")
        print(f"  Home: {has_home}")
    except Exception as e:
        print(f"  ERR: {e}")


# Now let's actually test what the user would see
print("\n\n" + "="*80)
print("MOST IMPORTANT: Test cai nguoi dung that su lam")
print("="*80)

# Scenario: User copy link, paste vao Safari address bar, hit Go
# This is what happens on iOS:
# 1. iOS sees URL 'https://netflix.com/?nftoken=XXX'
# 2. iOS check UL: domain 'netflix.com' is in Netflix app's associated domains
# 3. iOS fetches AASA: path '/', query 'nftoken=XXX' is NOT excluded
# 4. iOS opens Netflix app (Universal Link) - PROBLEM
# 5. Netflix app gets URL, tries to handle nftoken
# 6. If token format is NOT iOS FTL format → app fails → app re-opens URL in Safari as web fallback
# 7. Safari GET URL → 301 redirect → /unsupported (App Link page again, but for Android)

# So the question is: can the 296-char token be opened directly in iOS Netflix app?
# Test: When Netflix app opens, what request does it make?
# We can't test that directly. But we can check: what format does iOS Netflix app send to FTL API?

# Actually, the iOS FTL API was called with:
#  - ESN: NFAPPL-02-IPHONE8=1-PXA-... (iPhone 8)
#  - modelType: IPHONE8-1
#  - User-Agent: Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)
# So the token IS iOS FTL format. App should accept it.

# CONCLUSION: The 296-char iOS FTL token SHOULD work both for:
#   - iOS Safari → opens app via UL → app redeems with internal FTL → OK
#   - iOS Safari (paste in address bar) → if app intercepts via UL, same as above
#   - Web flow (Chrome/Edge) → 301 redirect → /unsupported → user sees App Link page
#   - Mobile Chrome with no app installed → 301 → /unsupported → user gets Android app link

# The "Lost your way" 404 happens when:
#   - URL is malformed (truncated, encoded wrong)
#   - Token is EXPIRED (after 1 hour)
#   - User's session expired (need new cookies)
#   - Network issue caused partial request

# Let me check: does the 296-char token that iOS FTL returns look right?
print(f"\nToken: {token}")
print(f"Length: {len(token)}")
print(f"Has 'pg=': {'pg%3D' in token or 'pg=' in token}")
print(f"Has 'v=3': {'v%3D3' in token or 'v=3' in token}")
print(f"Contains 'GAYiDgoM': {'GAYiDgoM' in token}")  # signature marker
print(f"Ends with something: {token[-40:]}")
