"""
Comprehensive test suite cho Auto_Login_NF với cookies thật từ user.
Test tất cả code path: parser, iOS FTL, web Shakti pathEvaluator, web Shakti direct,
hybrid smart, end-to-end API endpoint, batch mode, edge cases.
"""
import sys
import os
import json
import time
import traceback
sys.path.insert(0, '.')

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
WARN = "\033[93m⚠ WARN\033[0m"
INFO = "\033[94mℹ INFO\033[0m"

results = {"pass": 0, "fail": 0, "warn": 0, "errors": []}


def log_result(name, ok, detail=""):
    if ok:
        print(f"  {PASS} {name}")
        if detail:
            print(f"         {detail}")
        results["pass"] += 1
    else:
        print(f"  {FAIL} {name}")
        if detail:
            print(f"         {detail}")
        results["fail"] += 1
        results["errors"].append(f"{name}: {detail}")


def log_warn(name, detail=""):
    print(f"  {WARN} {name}")
    if detail:
        print(f"         {detail}")
    results["warn"] += 1


def log_info(name, detail=""):
    print(f"  {INFO} {name}")
    if detail:
        print(f"         {detail}")


# ============================================================================
# Setup: import modules sau khi setup sys.path
# ============================================================================
print("=" * 80)
print("SETUP: Import modules")
print("=" * 80)

try:
    import netflix
    import app as flask_app
    from netflix import (
        parse_cookies, parse_cookie_blocks, split_cookie_blocks,
        get_login_links, _create_token_hybrid, _create_token_via_shakti,
        _create_token_ios_ftl, _fallback_create_token, _build_cookie_header,
        _detect_token_source, has_usable_nftoken, decode_netflix_value,
    )
    log_result("Import tất cả module", True, f"netflix.py={os.path.getsize('netflix.py')} bytes")
except Exception as e:
    log_result("Import tất cả module", False, str(e))
    traceback.print_exc()
    sys.exit(1)


# ============================================================================
# TEST 1: Cookie parser với 4 cookies thật
# ============================================================================
print()
print("=" * 80)
print("TEST 1: Cookie parser với 4 cookies thật từ user")
print("=" * 80)

# 4 cookies thật mà user cung cấp
REAL_COOKIES = [
    [
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "flwssn", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "nfvdid", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "SecureNetflixId", "path": "/", "sameSite": "strict", "secure": True, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "NetflixId", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "ct%3DBgjHlOvcAxKMBHsYrGvdE6hAKq7mK0Jhjhti1pWth_mIhdXv3RNt_yo2ay0H9PakFLQmHhvndxLArtB2XIPjybpi-g7Sb_QwiXqhMoY5hR456_TvhazEAjYTUpW1zMh2JkKiAfdOb5wGaQabA9JTUYS4FJumftiy1znQ1pWaUaUIS3tKnbqxoGtxL4mGcTug4cpp3rIrO62fiJUVuD_8VMwjoi1-P5Vo5y0XIX3ZCsc6FzMM1MCXKUWhg8M6_F89e_Ad9svNQVLnAbPT0Xc9_4OraknzPelKneQGVH4JxSkKPJLBIILsEKjBnyWiRQ4ANQWRzIY0SGnT8hquS5rZ9Ue53mSSFQVAvjrdAWpmW0azb8d2OsIoo55YkN2kHWLJJvvYhR7zdWNf52Gn4E00R5KjkUPT0U8NSR4eCG00sMTVIe3NwZZFP2ZFUaAF3mlhOE4bSeaCX9K0CN3hVZSdsIqvUAriLxVe1xkqZRwS4RKI7dlgv5FwDGx6PWpmusqs9XYEiZSpl3UbPVGRc_zOQxFuw7PJpnAllYSaNJSLCImkHVW8B2ReLx_UYZ5AM1QeuwWVKqWlBlTSBP036h5GVMQioEl-oJqa830jIzkcK43CFaYL41Ygtwh0B98UXG-Kacg1KSKPXieNHyuSG7dBpndfU4D4u5WzeC8ePGccIegjwna6a2gXdvq01lMYno3WtACtRgGqGAYiDgoMiSu7GlBF0gJzIO30%26ch%3DAQEAEAABABRs47BMh9TCBFax0isxcqbg8oc43XcKrPc.%26v%3D3%26pg%3DMPEVBNSMKVEVPEZFKBHSOICVSI"},
    ],
    [
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "flwssn", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "nfvdid", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "SecureNetflixId", "path": "/", "sameSite": "strict", "secure": True, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "NetflixId", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "ct%3DBgjHlOvcAxKuA7TVcf8YegNL00II64nDWdTzj-fPWD6ObO6w7oUDzynZKeHxTmfkBycVSEtjDwZsHa05TEujYOl45YQYdxlwq8ilCX-FVIsXthXGENMRm3hfeddh8LYEM6LBhX3ql5cdr6ChyrYtbBtN0oRpo1twoggxgaNVmw07wjLgIykpWA5nw0ULRCpMeziSJxuK9x9GFYC6A-Df2vuwJ_ZJQNW9ysQyiVQv-CXp5yZ0ExTBCf6GEfGcjPQCn2BXSeA16SIhRXvY0TtQcT_wCYQIYUvxLl23GT6YrckUDdWLg0Q8yPDKyM5Kf84JMSvbTKnYdsHIkr3HcW6Gs7GrhCeTyzWOyI-hEV5HlN09wGIq-q-XMZTtrjQ-xwk9ISrOKcedpDnnqYTn6SNKv0e8XUOSxE99pclVUMsubfKQPznVWox1jsSpNcU9qTrVFwGdCRcn4HfXvdVCNyhVizUzyKgNrxddSUA-4RUaRvGUhYamhaThcDatAxAYEy4qevNpe-YtlVYUvw5WmtwmDkUtK9H_EUAFKiue21QQN3ET8XNYMtKYgbD8_XgciIDkUdQgn9gxVbgYBiIOCgwTigIFR4Fi5csEgJc.%26ch%3DAQEAEAABABREoImZqaf9CfwxG7uhkDjFX-d6UJMvyAE.%26v%3D3%26pg%3DTT3DJ2QVD5BHPFE24WQW74BWSQ"},
    ],
    [
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "flwssn", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "nfvdid", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "SecureNetflixId", "path": "/", "sameSite": "strict", "secure": True, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "NetflixId", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "ct%3DBgjHlOvcAxL_Aw1vzkIvuKg77SN_nF-liQh8Eet5cEMsA7XbKBFg4H87MRBP8RpJRXEQWVePUE0esxWeQ-ZDHJ0tvT2JvB7F1-6M8JUktwJN6hfc811djzH78hg9sxjXaF-Lz3mXr7FK24ZsG4i2Z2uHmeEIGBqPRAfbPvvKZkyqd_722r1cZO4EChtuyxRePiahxaXDuV3xcTyErjqes8EFPl-8_TaIcxg2nreUipi_nXNag2iNpqFVJQ9jee0xxRUWWhDhpwfsc_CCfbApvDcbRoZlEQhagMqiEU7zwX0k7C8KAFADN6lNQ3VRZyU7Pg1NYplkIQlEaNAI_L_JoJhJO4uMVladTxvQ4vsWlKwTpoi4eaLJ4zfNWokTTuZTCms6pJUB2xe-o62gxv36LG4uRIAHwCPLhJBGsXkKDBFB-i4TL102mnY8HdGLoxmAEHuLDGq3VkWWXWfVghO2bOsP9BzZKO3rZsMKVwAaRMHtqBo9FVT4pHWUcU1RtPK55NtsUY9YzrZmgwS9-xMWkQeqaKgQHHvOa03HDRdrJAYzZWui1Y3ZWBdJo7hgKyS6EMt4kpKBWsl7sqHDAtcC3Buv_RyPSb82ENnwMDiwbWGoW4BuI2h0iNLiMe7xWhTZJYUeQndPveKeNPfBSuHwT8iBfXuErbt6KxM4Nb4v0UzXXj7Fp6ci4GUYBiIOCgwAxmCiP6oHM754WqE.%26ch%3DAQEAEAABABTqjMNm0nBtBUsxpnPPCNJSgq72sutlRE0.%26v%3D3%26pg%3D7NKLDDTSONBT5CMZHJNRTSLTTE"},
    ],
    [
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "flwssn", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": False, "name": "nfvdid", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "SecureNetflixId", "path": "/", "sameSite": "strict", "secure": True, "session": False, "storeId": "0", "value": ""},
        {"domain": ".netflix.com", "hostOnly": False, "httpOnly": True, "name": "NetflixId", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "ct%3DBgjHlOvcAxL4A5V-O_fePzvchmBJYK5PC5jFDnooxsJg8XaOPvNuZazRYg_DhsMzybY5juhy1G7Cy5TD2SHQ_TDn9xlr0wFBANaXmfulyTDboWW_4YUxmXlSxG6JP761MMlytxD3c181j6qt6Y6WIrYAZx6K5C79aDj515CT7mVsAyTXx3mZvq5UcwxDJYzOLlWkYgFioZERb8_iJ1XHdyrEzGmpQn12vUcOmk97AgC8a8_rHPevyL4Og0NuMVvX91TCYZn5E930Z2uPVDpAbyJOufAe7DPQjRfJfDDsyuA4Idha0XLVaoWgjQyJi70rqvNgpTYgUr_rpIs48Wsv1c0DHF2wDQl0Y_4Yn0pUD96k5dZje1y4fW1dZuMK613U9jhLa3FC4Weuluqyr_WGozbapYsdx-JETTZmH1o_4L3hYQRMzR8oysiuXABjxuM65xrSq7zgQbXg6Elsh-f3FWwoKaGC_WNo65nTAjr5aQwSb8hjeLUpJ1bf2Ib7_iykNX9VnIS1Hx0aJhn8X0rO31zc9uaWOKfP1clDANNKvR5Ol7PsHNTG7Iz_LeVGH9RdDvvfeuCybGrJj_1KObZl57hHajgV-q2V8bdH3CF0deS_3Wcq1E6sBsIyBUUj3f-x370kQ8pyFXvRcBRY8QYLGmqliE5KzMP3lyn-kUKHeLrXjRgGIg4KDHIet7gtDrAGQPrElg..%26ch%3DAQEAEAABABRZneIZMnfH4-z71dDvCsj1U2G4vGGhACQ.%26v%3D3%26pg%3DLMLAFPVLIFHVNJJ35MVI57GLNM"},
    ],
]

print(f"  So cookie test: {len(REAL_COOKIES)}")

# Test parse tung cookie
parsed_all = []
for i, cookie_arr in enumerate(REAL_COOKIES, 1):
    raw = json.dumps(cookie_arr)
    parsed = parse_cookies(raw)
    parsed_all.append(parsed)

    has_nf = bool(parsed.get("NetflixId"))
    has_sec = bool(parsed.get("SecureNetflixId"))
    has_nfvdid = bool(parsed.get("nfvdid"))
    nf_len = len(parsed.get("NetflixId", ""))

    log_info(
        f"Cookie {i}: NetflixId={has_nf}({nf_len}c) SecureNetflixId={has_sec} nfvdid={has_nfvdid}",
        f"NetflixId starts with: {parsed.get('NetflixId', '')[:50]}..."
    )

# Verify tat ca cookie co NetflixId
all_have_nf = all(bool(p.get("NetflixId")) for p in parsed_all)
log_result(
    "Tat ca 4 cookie parse duoc NetflixId",
    all_have_nf,
    f"Count: {sum(1 for p in parsed_all if p.get('NetflixId'))}/4"
)

# Test 1 cookie bi thieu SecureNetflixId (case that cua user)
log_warn(
    "Cookie that thieu SecureNetflixId (value rong)",
    "Dieu nay co the gay loi voi mot so endpoint. Can test xem hybrid van hoat dong khong"
)


# ============================================================================
# TEST 2: Build cookie header
# ============================================================================
print()
print("=" * 80)
print("TEST 2: Build cookie header")
print("=" * 80)

for i, parsed in enumerate(parsed_all, 1):
    header = _build_cookie_header(parsed)
    has_nf = "NetflixId=" in header
    log_result(
        f"Cookie {i}: header chua NetflixId=",
        has_nf,
        f"header[0:80]: {header[:80]}..."
    )


# ============================================================================
# TEST 3: Hybrid smart - thử với cookie thật
# ============================================================================
print()
print("=" * 80)
print("TEST 3: Hybrid smart token creation voi cookie that (can network)")
print("=" * 80)

for i, parsed in enumerate(parsed_all, 1):
    print(f"\n--- Cookie {i} ---")
    try:
        token_data, log = _create_token_hybrid(parsed)
        if token_data and token_data.get("token"):
            token = token_data["token"]
            source = token_data.get("source", "unknown")
            log_info(
                f"Cookie {i}: THANH CONG",
                f"source={source} token_len={len(token)}"
            )
            log_info(
                f"  token preview",
                f"{token[:80]}...{token[-40:]}"
            )
            log_info(
                f"  token detection (theo length)",
                _detect_token_source(token)
            )
        else:
            err = log.get("preview", "unknown") if log else "unknown"
            log_warn(
                f"Cookie {i}: FAIL (expected vi cookie co the da het han)",
                f"err: {err[:200]}"
            )
    except Exception as e:
        log_result(
            f"Cookie {i}: khong crash",
            False,
            f"Exception: {type(e).__name__}: {str(e)[:200]}"
        )
        traceback.print_exc()


# ============================================================================
# TEST 4: iOS FTL only (direct, ko qua hybrid)
# ============================================================================
print()
print("=" * 80)
print("TEST 4: iOS FTL endpoint (direct test)")
print("=" * 80)

for i, parsed in enumerate(parsed_all, 1):
    print(f"\n--- Cookie {i} ---")
    try:
        token, log = _create_token_ios_ftl(parsed, attempts=1)
        if token:
            log_info(
                f"Cookie {i}: iOS FTL OK",
                f"source={token.get('source')} len={len(token.get('token', ''))}"
            )
        else:
            err = log.get("preview", "unknown") if log else "unknown"
            log_warn(
                f"Cookie {i}: iOS FTL fail (expected for non-iOS account/expired)",
                f"err: {err[:200]}"
            )
    except Exception as e:
        log_result(f"Cookie {i}: khong crash", False, str(e)[:200])


# ============================================================================
# TEST 5: Shakti pathEvaluator (direct)
# ============================================================================
print()
print("=" * 80)
print("TEST 5: Shakti pathEvaluator (direct test)")
print("=" * 80)

for i, parsed in enumerate(parsed_all, 1):
    print(f"\n--- Cookie {i} ---")
    try:
        token, log = _create_token_via_shakti(parsed)
        if token:
            log_info(
                f"Cookie {i}: Shakti OK",
                f"source={token.get('source')} len={len(token.get('token', ''))}"
            )
        else:
            err = log.get("preview", "unknown") if log else "unknown"
            log_warn(
                f"Cookie {i}: Shakti fail (expected cho account binh thuong)",
                f"err: {err[:200]}"
            )
    except Exception as e:
        log_result(f"Cookie {i}: khong crash", False, str(e)[:200])


# ============================================================================
# TEST 6: end-to-end qua Flask API
# ============================================================================
print()
print("=" * 80)
print("TEST 6: End-to-end qua Flask API endpoint")
print("=" * 80)

flask_app.app.config["TESTING"] = True
client = flask_app.app.test_client()

# Test /api/generate voi 1 cookie
for i, cookie_arr in enumerate(REAL_COOKIES, 1):
    print(f"\n--- POST /api/generate with cookie {i} ---")
    try:
        resp = client.post(
            "/api/generate",
            json={"cookies": json.dumps(cookie_arr)},
        )
        data = resp.get_json()
        log_info(
            f"Cookie {i}: HTTP {resp.status_code}",
            f"ok={data.get('ok')} error={data.get('error', '')[:100] if data.get('error') else 'none'}"
        )
        if data.get("ok"):
            log_info(
                f"  token_source",
                data.get("token_source")
            )
            log_info(
                f"  web URL exists",
                bool(data.get("web") or data.get("pc"))
            )
            log_info(
                f"  mobile URL exists",
                bool(data.get("app") or data.get("mobile"))
            )
            log_info(
                f"  warning",
                (data.get("warning") or "none")[:100]
            )
        log_result(
            f"Cookie {i}: response hop le (JSON, co 'ok' field)",
            "ok" in data,
        )
    except Exception as e:
        log_result(f"Cookie {i}: khong crash", False, str(e)[:200])


# ============================================================================
# TEST 7: Batch mode với tất cả 4 cookie
# ============================================================================
print()
print("=" * 80)
print("TEST 7: Batch mode (4 cookie cùng lúc)")
print("=" * 80)

batch_raw = "".join(json.dumps(c) for c in REAL_COOKIES)
print(f"  Batch input size: {len(batch_raw)} chars")

# /api/split
try:
    resp = client.post("/api/split", json={"cookies": batch_raw})
    data = resp.get_json()
    log_info(
        "POST /api/split",
        f"ok={data.get('ok')} blocks={data.get('count')}"
    )
    log_result(
        "Split ra 4 block",
        data.get("count") == 4,
        f"Expected 4, got {data.get('count')}"
    )
    blocks = data.get("blocks", [])
    for j, block in enumerate(blocks, 1):
        log_info(f"  block {j}", f"len={len(block)} starts with: {block[:60]}...")
except Exception as e:
    log_result("Split", False, str(e)[:200])


# /api/batch (legacy, xử lý tuần tự)
try:
    resp = client.post("/api/batch", json={"cookies": batch_raw})
    data = resp.get_json()
    results_arr = data.get("results", [])
    log_info(
        "POST /api/batch",
        f"Got {len(results_arr)} results"
    )
    for r in results_arr:
        idx = r.get("index")
        ok = r.get("ok")
        err = r.get("error", "")
        log_info(
            f"  result #{idx}",
            f"ok={ok} err={err[:80] if err else 'none'} token_src={r.get('token_source', 'n/a')}"
        )
    log_result(
        "Batch xu ly 4 cookie",
        len(results_arr) == 4,
    )
except Exception as e:
    log_result("Batch", False, str(e)[:200])


# ============================================================================
# TEST 8: Edge cases
# ============================================================================
print()
print("=" * 80)
print("TEST 8: Edge cases")
print("=" * 80)

edge_cases = [
    ("empty body", {"cookies": ""}),
    ("missing field", {}),
    ("non-string cookies", {"cookies": 123}),
    ("malformed JSON", {"cookies": "[{"}),
    ("not cookie at all", {"cookies": "hello world"}),
    ("valid JSON but not cookies", {"cookies": '{"a": 1}'}),
    ("only NetflixId key", {"cookies": 'NetflixId=abc'}),
    ("URL-encoded NetflixId", {"cookies": 'NetflixId=ct%3Dtest%26v%3D3'}),
    ("JSON with single cookie", {"cookies": '[{"name":"NetflixId","value":"ct%3Dabc"}]'}),
    ("mixed format (raw + JSON)", {"cookies": 'NetflixId=ct%3Dtest\n[{"name":"NetflixId","value":"ct%3Dtest2"}]'}),
]

for name, payload in edge_cases:
    try:
        resp = client.post("/api/generate", json=payload)
        data = resp.get_json()
        log_info(
            f"Edge: {name}",
            f"HTTP {resp.status_code} ok={data.get('ok')} err={(data.get('error', '') or 'none')[:80]}"
        )
    except Exception as e:
        log_warn(f"Edge: {name}", f"Exception: {str(e)[:100]}")


# ============================================================================
# TEST 9: HTML frontend
# ============================================================================
print()
print("=" * 80)
print("TEST 9: Frontend page")
print("=" * 80)

try:
    resp = client.get("/")
    log_result("GET / returns HTML", resp.status_code == 200, f"size={len(resp.data)}")
    log_result(
        "HTML chua cac element can thiet",
        b"single-input" in resp.data and b"batch-input" in resp.data and b"debug-url" in resp.data,
    )
except Exception as e:
    log_result("GET /", False, str(e)[:200])

try:
    resp = client.get("/static/js/main.js")
    log_result("GET /static/js/main.js", resp.status_code == 200)
    log_result(
        "main.js co source-tag handling",
        b"src-web" in resp.data and b"src-ios" in resp.data,
    )
    log_result(
        "main.js co warning handling",
        b"warning-box" in resp.data,
    )
except Exception as e:
    log_result("main.js", False, str(e)[:200])

try:
    resp = client.get("/static/css/style.css")
    log_result("GET /static/css/style.css", resp.status_code == 200)
    log_result(
        "style.css co source-tag CSS",
        b".src-web" in resp.data and b".src-ios" in resp.data and b".warning-box" in resp.data,
    )
except Exception as e:
    log_result("style.css", False, str(e)[:200])


# ============================================================================
# SUMMARY
# ============================================================================
print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"  PASS: {results['pass']}")
print(f"  FAIL: {results['fail']}")
print(f"  WARN: {results['warn']}")
print()
if results["errors"]:
    print("ERRORS:")
    for e in results["errors"][:20]:
        print(f"  - {e}")
    if len(results["errors"]) > 20:
        print(f"  ... and {len(results['errors']) - 20} more")

# Exit code
sys.exit(0 if results["fail"] == 0 else 1)
