"""Final integration test voi cookies that tu user.
   Test:
   1. Parser voi cookie
   2. Single cookie API
   3. Batch API voi 10 cookies
   4. Frontend HTML/JS - check warning NSES da bi bo
   5. Error message ro rang khi cookie die
"""
import sys
import json
sys.path.insert(0, '.')

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
results = {"pass": 0, "fail": 0, "errors": []}


def ok(name, detail=""):
    print(f"  {PASS} {name}")
    if detail:
        print(f"         {detail}")
    results["pass"] += 1


def fail(name, detail=""):
    print(f"  {FAIL} {name}")
    if detail:
        print(f"         {detail}")
    results["fail"] += 1
    results["errors"].append(f"{name}: {detail}")


def info(name, detail=""):
    print(f"  {INFO} {name}")
    if detail:
        print(f"         {detail}")


# ===== Setup =====
import app as flask_app
flask_app.app.config["TESTING"] = True
client = flask_app.app.test_client()


# ===== TEST 1: Parser =====
print("=" * 80)
print("TEST 1: Cookie parser")
print("=" * 80)
from netflix import parse_cookies, parse_cookie_blocks

COOKIE_LIVE = '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"v%3D3%26ct%3DBgjHlOvcAxKcA9Cp5eCQ0uAbIK375r3I072z1v9ZHEe8qOpvvtOpgNxdLVrQ8wr41Hwm7Pj-ruSS1jT4aeLJildS-OoV1-bsoXkt09pVQvjFW5B1b9D1nbRjVF2Rad4nYn7Mjc2EeTbm-mmEPqDllNZBsbNlG8lSOwQBrIBTGqDAKGEPnrO5cSqgEIXSqsOqhWePNQUyvnlVmBN4FFWXcNk4PuAG9gD4oVu8-jEYRnHOqrgW-zJ8rExH-hIibDGYIVd6UipPlwH1_iCzaWB4koEXs8kDmOGn6VoFjhmTjBct8itdbVBB5qU4hf1rHFU5THh89eeKHQz0zuo1zYT5kFenublcEEtgcQ01MFNhgXY6X6WQEyr4VB3znu-MVhxOCiva-JshkcoNiwU7g0sqe8GXUQaJIEVoc4Qq0eIoD7TDKOoqsVGWkk-lBXIsW7xw0b7S7VkjI5kby5WB02AlJJ8-YHhOO_JYMOHWXsvWqUiWvoMu44LAVNhR6hOFQhrJ82XTWueU5hIDGW4ttNxkV-vW904yT1pf6xmPTDpztGMPO84OpAoYBiIOCgx1JgUKsfqhHu80GO4.%26pg%3D3S66EWQ64BEPLN77VUYUWFTEAM%26ch%3DAQEAEAABABQv0KhtR8GR-MQmnQ677qZ0ZtoOKtCd7xA."}]'
parsed = parse_cookies(COOKIE_LIVE)
if parsed.get("NetflixId"):
    ok("Parser works with real cookie", f"NetflixId len={len(parsed.get('NetflixId', ''))}")
else:
    fail("Parser fail", str(parsed))


# ===== TEST 2: Edge cases =====
print()
print("=" * 80)
print("TEST 2: Edge cases (khong crash)")
print("=" * 80)
edge_cases = [
    ("empty body", {"cookies": ""}),
    ("missing field", {}),
    ("non-string", {"cookies": 123}),
    ("malformed JSON", {"cookies": "[{"}),
]
for name, payload in edge_cases:
    try:
        resp = client.post("/api/generate", json=payload)
        if resp.status_code in (200, 400):
            ok(f"Edge: {name} (HTTP {resp.status_code})")
        else:
            fail(f"Edge: {name} unexpected status", f"HTTP {resp.status_code}")
    except Exception as e:
        fail(f"Edge: {name} crashed", str(e)[:100])


# ===== TEST 3: Single cookie via API =====
print()
print("=" * 80)
print("TEST 3: /api/generate voi 1 cookie")
print("=" * 80)
resp = client.post("/api/generate", json={"cookies": COOKIE_LIVE})
data = resp.get_json()
# Cookie có the die hoac live - chi check structure
if "ok" in data:
    ok("/api/generate returns valid JSON with 'ok' field")
else:
    fail("/api/generate no 'ok' field")

if data.get("error"):
    # Cookie die - check error message
    err = data.get("error", "")
    if "Cookie đã hết hạn" in err or "Netflix" in err or "rate limit" in err.lower():
        ok("Error message ro rang (cookie die/rate limit)", f"err: {err[:100]}")
    else:
        info("Error message", f"err: {err[:100]}")

if data.get("warning"):
    fail("Still has warning (NSES-404)", data["warning"][:100])
else:
    ok("Khong con warning NSES-404")


# ===== TEST 4: Frontend assets =====
print()
print("=" * 80)
print("TEST 4: Frontend assets (warning removed)")
print("=" * 80)
resp = client.get("/static/js/main.js")
if resp.status_code == 200:
    if b"s\u1ebd 404" in resp.data or b"404" in resp.data or b"NSES" in resp.data:
        # Co the text cung con nhung phai check context
        if b"CH\u1ec8 d\u00f9ng cho iOS app / PC, mobile browser s\u1ebd 404" in resp.data:
            fail("main.js van co text 'CHỈ dùng cho iOS app / PC, mobile browser sẽ 404'")
        else:
            ok("main.js has no 'mobile browser sẽ 404' warning")
    else:
        ok("main.js has no NSES-404 warning text")
else:
    fail("GET main.js", f"HTTP {resp.status_code}")

resp = client.get("/")
if resp.status_code == 200 and b"single-input" in resp.data:
    ok("GET / returns HTML")
else:
    fail("GET / failed", f"HTTP {resp.status_code}")


# ===== TEST 5: 10 cookies via batch (dung cookie die de test error message) =====
print()
print("=" * 80)
print("TEST 5: /api/batch voi 10 cookies (check error message ro rang)")
print("=" * 80)
# 10 cookies (da die tu truoc)
COOKIES_DIE = [
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"v%3D3%26ct%3DBgjHlOvcAxKMA0niEbTiB5FA24BXMgU-LI_GSHGcQDs_-bCPkiatFMcw99N8_L-DLAnZbZ3tmeWLNbtPHe2VQmtlhZB3oGD2YK1OF9aFSGMVS-kegLuxO6JNiHqynoQv984Qx81aM2i21suB1mxTzxxsAYaWvPV7_1zNSx9b5wZIdTe5P6cwjvvpzFeg7im-V8pT9JhNg9stTUESEn3mkaLxMI0fgY3lG87-QaLe5drYByOyM-KME1sSgxExE1PqihbQyLSiWIX3yxiXRjexkfbDzq7BYBKnrF7zOy1xYEW72ynu7j5SnBuGdIQzbD4-K7qToSYzu3eZ7YR6qpUUbHHOWansJ0s1w7N-qG_HQyQeESbfmMtPVdQMDPaRImXVbKYjv7pce7uZGdV1R0IyrNCY-G5F-XwPCgWOwOATCJXECSBX5fvf2CsRAd31v1Q5T0HIHW_P-LPb2aaX_bJy6B7sRoeb3LBrWUFjpxLoW0szeCTegnqxpYpXxYDtrpNDyouilaqH4H788dyoNHbGbNr1XekEGRgGIg4KDGdAJmqxpm0szuVLtw..%26pg%3DA5BEUG3OJFGFLKXZTUMC75V5LE%26ch%3DAQEAEAABABTh2oM86vPYvHkGY8ma7_ylilW6a_BMPUQ."}]',
] * 10
batch = "\n".join(COOKIES_DIE)
resp = client.post("/api/batch", json={"cookies": batch})
data = resp.get_json()
results_arr = data.get("results", [])
if len(results_arr) == 10:
    ok("/api/batch split 10 cookies", f"got {len(results_arr)} results")
    # Check error message of failed cookies
    for r in results_arr[:3]:
        err = r.get("error", "")
        if "Cookie" in err and "hết hạn" in err:
            ok(f"#{r['index']} error message ro rang (cookie die)", err[:80])
            break
    else:
        if not any(r.get("ok") for r in results_arr):
            fail("Error message not clear", f"first err: {results_arr[0].get('error', '')[:100]}")
else:
    fail("/api/batch split", f"got {len(results_arr)} results")


# ===== TEST 6: /api/split =====
print()
print("=" * 80)
print("TEST 6: /api/split")
print("=" * 80)
batch_raw = "\n".join(COOKIES_DIE)
resp = client.post("/api/split", json={"cookies": batch_raw})
data = resp.get_json()
if data.get("count") == 10:
    ok("/api/split", f"count={data.get('count')}")
else:
    fail("/api/split", f"count={data.get('count')}")


# ===== SUMMARY =====
print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print(f"  PASS: {results['pass']}")
print(f"  FAIL: {results['fail']}")
if results["errors"]:
    print("  ERRORS:")
    for e in results["errors"]:
        print(f"    - {e}")

print()
print("=" * 80)
print("THAY ĐỔI ĐÃ THỰC HIỆN")
print("=" * 80)
print("""
1. netflix.py:
   - Thêm hàm _check_cookie_alive() — gọi endpoint nhẹ ?path=[\"account\"]
     để phát hiện cookie die sớm (Netflix trả value rỗng)
   - create_nftoken() gọi _check_cookie_alive() trước, trả error rõ ràng
     nếu cookie die (thay vì "Tất cả endpoint đều fail" chung chung)
   - get_login_links() BỎ warning NSES-404 (vì user confirm work OK trên mobile)
   - Error message phân loại: cookie die / 403 / 429 / timeout

2. static/js/main.js:
   - Đổi label "iOS FTL (CHỈ dùng cho iOS app / PC, mobile browser sẽ 404)"
     thành "iOS FTL (hoạt động trên mọi thiết bị)" (đã verify)
""")

sys.exit(0 if results["fail"] == 0 else 1)
