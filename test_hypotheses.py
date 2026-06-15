"""Test nhung giai thuyet khac co the gay NSES-404."""
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

# Giai thuyet 1: User copy/paste link nhung bi mat ki tu (do messenger truncate)
print("=== GIAI THUYET 1: Link bi truncated ===")
web_url = PC_LOGIN_BASE + token
truncated_url = web_url[:200] + "..."  # gia su bi cat
print(f"  Original: {web_url[:80]}...{web_url[-40:]}")
print(f"  Truncated len: {len(truncated_url)} (vs {len(web_url)})")
session = requests.Session()
session.verify = False
try:
    resp = session.get(
        truncated_url,
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1"},
        timeout=15,
        allow_redirects=False,
    )
    print(f"  Truncated status: {resp.status_code}")
    print(f"  Location: {resp.headers.get('Location', '')[:200]}")
except Exception as e:
    print(f"  ERR: {e}")


# Giai thuyet 2: Token duoc URL-encode khi paste vao browser
print("\n=== GIAI THUYET 2: Token bi URL-encode khi paste ===")
import urllib.parse
encoded_token = urllib.parse.quote(token, safe="")
encoded_url = PC_LOGIN_BASE + encoded_token
print(f"  Encoded: {encoded_url[:100]}...")
session = requests.Session()
session.verify = False
try:
    resp = session.get(
        encoded_url,
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1"},
        timeout=15,
        allow_redirects=False,
    )
    print(f"  Encoded status: {resp.status_code}")
    print(f"  Location: {resp.headers.get('Location', '')[:200]}")
except Exception as e:
    print(f"  ERR: {e}")


# Giai thuyet 3: User paste vao Chrome mobile nhung chrome redirect
print("\n=== GIAI THUYET 3: Chrome mobile user-agent ===")
session = requests.Session()
session.verify = False
try:
    resp = session.get(
        web_url,
        headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"},
        timeout=15,
        allow_redirects=False,
    )
    print(f"  Chrome Mobile status: {resp.status_code}")
    print(f"  Location: {resp.headers.get('Location', '')[:200]}")
except Exception as e:
    print(f"  ERR: {e}")


# Giai thuyet 4: Telegram mini-app browser
print("\n=== GIAI THUYET 4: Telegram in-app browser ===")
session = requests.Session()
session.verify = False
try:
    resp = session.get(
        web_url,
        headers={"User-Agent": "Telegram/10 (iPhone; iOS 16.0; Scale/3.00)"},
        timeout=15,
        allow_redirects=False,
    )
    print(f"  Telegram status: {resp.status_code}")
    print(f"  Location: {resp.headers.get('Location', '')[:200]}")
except Exception as e:
    print(f"  ERR: {e}")


# Giai thuyet 5: User paste link nhung them ky tu prefix/suffix
print("\n=== GIAI THUYET 5: Link co prefix/suffix (vi du chat messenger) ===")
prefixed_url = "https://t.me/share/url?url=" + web_url
print(f"  Prefixed: {prefixed_url[:100]}...")
session = requests.Session()
session.verify = False
try:
    resp = session.get(
        prefixed_url,
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1"},
        timeout=15,
        allow_redirects=False,
    )
    print(f"  Prefixed status: {resp.status_code}")
    print(f"  Location: {resp.headers.get('Location', '')[:200]}")
except Exception as e:
    print(f"  ERR: {e}")


# Giai thuyet 6: User copy/paste NHIEU lan trong cung 1 phien (token co the bi revoke sau lan use đầu)
print("\n=== GIAI THUYET 6: Token used 2 lan (kha nang bi revoke) ===")
session = requests.Session()
session.verify = False
try:
    # Lan 1
    resp1 = session.get(
        web_url,
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1"},
        timeout=15,
        allow_redirects=True,
    )
    print(f"  Lan 1 final URL: {resp1.url[:100]}")
    # Lay cookies moi set
    new_cookies = dict(session.cookies)

    # Lan 2 voi cung URL nhung cookies moi (nhu user vua login xong paste link lan nua)
    resp2 = session.get(
        web_url,
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1"},
        timeout=15,
        allow_redirects=True,
    )
    print(f"  Lan 2 final URL: {resp2.url[:100]}")
    if "NSES-404" in resp2.text or "Lost your way" in resp2.text:
        print(f"  [NSES-404] Lan 2 bi loi!")
    else:
        print(f"  [OK] Lan 2 khong bi loi")
except Exception as e:
    print(f"  ERR: {e}")


# Giai thuyet 7: Cookie da het han (cu hon 30p)
print("\n=== GIAI THUYET 7: Token cu (>30p) ===")
import time
# Generate token, doi 2s, test, doi lau hon
# (thuc te test 5 phut, nhung de demo ta chi doi 5s)
print("  [INFO] Real-world test can wait 30+ phut. Demo bằng cách xem response với token mới vừa tạo")
session = requests.Session()
session.verify = False
resp = session.get(
    web_url,
    headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1"},
    timeout=15,
    allow_redirects=True,
)
print(f"  Status: {resp.status_code}, URL: {resp.url[:100]}")


# Giai thuyet 8: User paste link nhanh 2 lan (double-click)
print("\n=== GIAI THUYET 8: Race condition (double-click) ===")
# Test 2 request song song voi cung token
import concurrent.futures

def get_url(url, ua):
    s = requests.Session()
    s.verify = False
    return s.get(url, headers={"User-Agent": ua}, timeout=15, allow_redirects=False)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    futs = [
        ex.submit(get_url, web_url, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1"),
        ex.submit(get_url, web_url, "Mozilla/5.0 (Linux; Android 13) Chrome/120.0.0.0 Mobile"),
    ]
    for i, f in enumerate(futs, 1):
        r = f.result()
        print(f"  Request {i}: {r.status_code} {r.headers.get('Location', '')[:80]}")
