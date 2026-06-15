"""Check Universal Link claim behavior with token."""
import sys
import json
import re
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from netflix import _create_token_hybrid, parse_cookies, PC_LOGIN_BASE

with open('cookies_test.json', 'r', encoding='utf-8') as f:
    REAL_COOKIES = json.load(f)

parsed = parse_cookies(json.dumps(REAL_COOKIES[0]))
token_data, _ = _create_token_hybrid(parsed)
token = token_data["token"]

# Get AASA
print("=== Netflix AASA file ===")
resp = requests.get("https://www.netflix.com/.well-known/apple-app-site-association", timeout=15, verify=False)
aasa = resp.json()
print(f"  apps in applinks: {len(aasa.get('applinks', {}).get('apps', []))}")
print(f"  details count: {len(aasa.get('applinks', {}).get('details', []))}")
# Print exclude rules for first detail
for d in aasa["applinks"]["details"]:
    print(f"  App: {d.get('appID')}")
    excludes = [c for c in d.get("components", []) if c.get("exclude")]
    print(f"  Exclude count: {len(excludes)}")
    # Find related to nftoken
    for c in excludes:
        if "?" in str(c) or "nftoken" in str(c):
            print(f"    {c}")
    # Check if /?* is excluded
    has_question = any(c.get("/") == "/?*" for c in excludes)
    print(f"  Has '/?*' exclude: {has_question}")


# Simulate iOS Safari without app installed (just browser)
print("\n=== iOS Safari WITH Netflix app installed (would claim via UL) ===")
print("  → Universal Link handler would intercept → open Netflix app")
print("  → If app not installed → fall through to Safari → 301 to /unsupported")
print("  → User sees /unsupported page (App Link page) — this is the FLOW")
print()
print("=== Kiem tra: Khi paste URL vao Safari address bar (khong phai click) ===")
print("  → Safari xử lý như web thường → 301 redirect → login OK")


# Test the actual case that fails for users
print("\n=== Test: Mở bằng iOS Safari + Netflix app installed (simulate) ===")
# Apple App Site Association
# NetFlix iOS app claims các path: /title/*, /browse/*, /watch/*, etc.
# Exclude: /?*, /login*, /unsupported
# → Khi user paste 'https://netflix.com/?nftoken=XXX' vào Safari:
#   - Safari thấy path '/', query 'nftoken'
#   - Check AASA: path '/?*' bị exclude → Safari xử lý URL
#   - Safari GET URL → Netflix server → 301 redirect
#   - User thấy Netflix login thành công

# Test full flow in browser-like manner
print("\n=== Test FULL iOS Safari simulation ===")
session = requests.Session()
session.verify = False

# iOS Safari with NetflixId cookie
for k, v in parsed.items():
    if v:
        session.cookies.set(k, v, domain=".netflix.com")

# Step 1: Visit nftoken URL
web_url = PC_LOGIN_BASE + token
print(f"  URL: {web_url[:80]}...")

resp = session.get(
    web_url,
    headers={
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    },
    timeout=20,
    allow_redirects=True,
)
print(f"  Final URL: {resp.url}")
print(f"  Final status: {resp.status_code}")
print(f"  Cookies: {list(session.cookies.keys())}")
print(f"  Body length: {len(resp.text)}")

# Check for various error patterns
signals = {
    "NSES-404": "NSES-404" in resp.text,
    "Lost your way": "Lost your way" in resp.text,
    "Sign In button": 'id="signIn"' in resp.text or 'href="/login"' in resp.text,
    "pageLoadError": "pageLoadError" in resp.text,
    "profile selector": "profile" in resp.text.lower() and "Profile" in resp.text,
    "browse content": 'id="browse"' in resp.text or 'class="lolomo' in resp.text,
    "title 80057281": '"80057281"' in resp.text,  # Stranger Things
    "redirect to login": "/login" in resp.url,
    "redirect to /browse": "/browse" in resp.url,
    "redirect to /unsupported": "/unsupported" in resp.url,
}
print(f"\n  Page signals:")
for k, v in signals.items():
    print(f"    {k}: {v}")

# Check if there's any pageLoadError
if "pageLoadError" in resp.text:
    # Extract the error
    m = re.search(r'pageLoadError[^"]*"([^"]+)"', resp.text)
    if m:
        print(f"  pageLoadError: {m.group(1)[:200]}")

# Also check the html title
m = re.search(r'<title>([^<]+)</title>', resp.text)
if m:
    print(f"  Page title: {m.group(1)[:100]}")
