"""
Netflix Login Link Generator

Multi-strategy generator: thử nhiều endpoint, scope, và profile khác nhau
để tối đa khả năng tạo token từ các cookie ở nhiều format khác nhau.

Endpoint chính: https://android13.prod.ftl.netflix.com/graphql
Operation: CreateAutoLoginToken (persisted query)

Ref: github.com/harshitkamboj/Netflix-NFToken-Generator
"""
import json
import re
import random
import time
from datetime import datetime, timezone

import requests
from urllib3.exceptions import InsecureRequestWarning

from config import PC_LOGIN_BASE, MOBILE_LOGIN_BASE

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ─── Cookie keys ───────────────────────────────────────────────────────────────

COOKIE_KEYS = ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn", "gsid")

# ─── Multi-strategy configuration ────────────────────────────────────────────────

# Strategy = (graphql_url, scope, user_agent, description)
STRATEGIES = [
    # Strategy 0: Android 13 (original, most common)
    (
        "https://android13.prod.ftl.netflix.com/graphql",
        {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
        "Android 13 — WEBVIEW_MOBILE_STREAMING",
    ),
    # Strategy 1: Android 13, INHOME_COALESCE scope
    (
        "https://android13.prod.ftl.netflix.com/graphql",
        {"scope": "INHOME_COALESCE"},
        "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
        "Android 13 — INHOME_COALESCE",
    ),
    # Strategy 2: Android 13, WEBVIEW_MOBILE_NEXT
    (
        "https://android13.prod.ftl.netflix.com/graphql",
        {"scope": "WEBVIEW_MOBILE_NEXT"},
        "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
        "Android 13 — WEBVIEW_MOBILE_NEXT",
    ),
    # Strategy 3: web endpoint alternative (persisted query v101)
    (
        "https://android13.prod.ftl.netflix.com/graphql",
        {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "Mozilla/5.0 (Linux; Android 13; M2007J3SG Build/TQ1A.230205.001.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.152 Safari/537.36",
        "Android Chrome UA",
    ),
    # Strategy 4: TV/Xiaomi variant
    (
        "https://android13.prod.ftl.netflix.com/graphql",
        {"scope": "TV8K_STREAMING"},
        "com.netflix.mediaclient/238320093 (Linux; U; Android 11; ro; M2102K1G; Build/RKQ1.200826.002; Cronet/TTWVersion.13370037)",
        "Android TV",
    ),
    # Strategy 5: Fallback web prod
    (
        "https://web.prod.ftl.netflix.com/graphql",
        {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
        "Web FTL — WEBVIEW_MOBILE_STREAMING",
    ),
]

GRAPHQL_PAYLOAD_BASE = {
    "operationName": "CreateAutoLoginToken",
    "extensions": {
        "persistedQuery": {
            "version": 102,
            "id": "76e97129-f4b5-41a0-a73c-12e674896849",
        }
    },
}

BASE_HEADERS_COMMON = {
    "Accept": "multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.netflix.com",
    "Referer": "https://www.netflix.com/",
}


# ─── Cookie parser ────────────────────────────────────────────────────────────

def _decode_cookie_value(value: str) -> str:
    if isinstance(value, str) and "%" in value:
        try:
            import urllib.parse
            return urllib.parse.unquote(value)
        except Exception:
            return value
    return value


def split_cookie_blocks(raw: str) -> list:
    """
    Tách input thành nhiều block cookie.
    Hỗ trợ:
    - ---- separator
    - JSON arrays
    - Raw: SecureNetflixId= đứng trước NetflixId= (mỗi dòng riêng)
    - Raw: NetflixId= đứng đầu (mỗi dòng riêng)
    - Raw: mỗi cặp key=value riêng trên 1 dòng
    - Paragraphs (dòng trắng ngăn cách)
    """
    text = raw.strip()
    if not text:
        return []

    # 1. ---- separator
    if "----" in text:
        return [b.strip() for b in text.split("----") if b.strip()]

    # 2. Multiple JSON arrays
    blocks = []
    depth = 0
    start = -1
    in_str = False
    escape = False
    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if in_str:
            if c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            continue
        if c == "[":
            if depth == 0:
                start = i
            depth += 1
        elif c == "]":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    blocks.append(text[start:i + 1])
                    start = -1
    if len(blocks) >= 2:
        return blocks

    # 3. Split bằng dòng trắng lớn trước (phòng batch multi-line)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs

    # 4. Dòng bắt đầu bằng SecureNetflixId= HOẶC NetflixId= → mỗi dòng là 1 block
    # Đây là pattern phổ biến nhất trong batch mới: mỗi dòng là 1 cookie
    lines = text.split("\n")
    line_blocks = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Dòng bắt đầu block mới
        if stripped.startswith("SecureNetflixId=") or stripped.startswith("NetflixId="):
            if current:
                joined = " ".join(current)
                if joined not in line_blocks:
                    line_blocks.append(joined)
            current = [stripped]
        else:
            current.append(stripped)

    if current:
        joined = " ".join(current)
        if joined not in line_blocks:
            line_blocks.append(joined)

    if len(line_blocks) >= 2:
        return line_blocks

    # 5. Raw: dùng anchor NetflixId= hoặc SecureNetflixId= ở đầu dòng / sau \n
    anchor_pat = re.compile(
        r"(?:^|\n)\s*(NetflixId=|SecureNetflixId=)",
        re.IGNORECASE
    )
    anchors = list(anchor_pat.finditer(text))
    if len(anchors) >= 2:
        raw_blocks = []
        for i, m in enumerate(anchors):
            start = m.start()
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
            chunk = text[start:end].strip()
            if chunk:
                raw_blocks.append(chunk)
        if len(raw_blocks) >= 2:
            return raw_blocks

    # 6. Nhiều NetflixId= trong text
    netflix_positions = [m.start() for m in re.finditer(r"\bNetflixId=", text)]
    if len(netflix_positions) >= 2:
        raw_blocks = []
        for i, start in enumerate(netflix_positions):
            end = netflix_positions[i + 1] if i + 1 < len(netflix_positions) else len(text)
            chunk = text[start:end].strip()
            if chunk:
                raw_blocks.append(chunk)
        if len(raw_blocks) >= 2:
            return raw_blocks

    # 7. Fallback: 1 block
    return [text]


def _fill_missing_shared_cookies(block_dicts: list) -> list:
    """
    Quét toàn batch để tìm nfvdid từ bất kỳ block nào có nó.
    Sau đó gán cho các block thiếu.
    Thứ tự ưu tiên: block cùng profile gần nhất > block gần nhất trong batch.
    """
    if not block_dicts:
        return block_dicts

    # Tìm tất cả nfvdid trong batch
    all_nfvdids = []
    for cd in block_dicts:
        if cd.get("nfvdid"):
            all_nfvdids.append(cd["nfvdid"])

    if not all_nfvdids:
        return block_dicts

    # Gán nfvdid cho block thiếu
    for cd in block_dicts:
        if not cd.get("nfvdid") and all_nfvdids:
            # Ưu tiên dùng nfvdid đầu tiên tìm được
            cd["nfvdid"] = all_nfvdids[0]

    return block_dicts


def parse_cookies(raw: str) -> dict:
    """Parse cookie string thành dict, hỗ trợ nhiều format."""
    text = raw.strip()
    cookie_dict: dict = {}

    # Thử parse JSON
    data = None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    if isinstance(data, list):
        for cookie in data:
            if isinstance(cookie, dict):
                name = cookie.get("name")
                value = cookie.get("value")
                if name in COOKIE_KEYS and isinstance(value, str):
                    cookie_dict[name] = _decode_cookie_value(value)
    elif isinstance(data, dict):
        if any(key in data for key in COOKIE_KEYS):
            for key in COOKIE_KEYS:
                value = data.get(key)
                if isinstance(value, str):
                    cookie_dict[key] = _decode_cookie_value(value)
        elif isinstance(data.get("cookies"), list):
            for cookie in data["cookies"]:
                name = cookie.get("name")
                value = cookie.get("value")
                if name in COOKIE_KEYS and isinstance(value, str):
                    cookie_dict[name] = _decode_cookie_value(value)

    # Regex patterns — nfvdid mới có format BQFmAAEB... (base64 với . và -)
    raw_patterns = {
        "NetflixId": r"(?<!\w)NetflixId=([^;,\s]+)",
        "SecureNetflixId": r"(?<!\w)SecureNetflixId=([^;,\s]+)",
        # FIX: nfvdid format mới là BQFmAAEB... chứa cả . và -
        "nfvdid": r"(?<!\w)nfvdid=([A-Za-z0-9_\-\.]+)",
        "OptanonConsent": r"(?<!\w)OptanonConsent=([^;,\s]+)",
        "flwssn": r"(?<!\w)flwssn=([^;,\s]+)",
        "gsid": r"(?<!\w)gsid=([^;,\s]+)",
    }

    for key in COOKIE_KEYS:
        if key in cookie_dict:
            continue
        match = re.search(raw_patterns[key], text)
        if match:
            cookie_dict[key] = _decode_cookie_value(match.group(1))

    return cookie_dict


def parse_cookie_blocks(raw: str) -> list:
    """Parse toàn bộ input thành list cookie dict, bù nfvdid toàn batch."""
    blocks = split_cookie_blocks(raw)
    parsed_blocks = [parse_cookies(block) for block in blocks]
    parsed_blocks = [cd for cd in parsed_blocks if cd]
    return _fill_missing_shared_cookies(parsed_blocks)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _fmt_expiry(expiry) -> str:
    if not expiry:
        return "Không xác định"
    try:
        ts = int(expiry)
        if ts > 1e12:
            ts //= 1000
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(expiry)


def _build_result(token: str, expiry, strategy_name: str) -> dict:
    return {
        "ok": True,
        "pc": PC_LOGIN_BASE + token,
        "mobile": MOBILE_LOGIN_BASE + token,
        "expiry": _fmt_expiry(expiry),
        "build_id": "android/63884",
        "strategy": strategy_name,
    }


def _build_cookie_header(cookies_dict: dict) -> str:
    """Build cookie header với tất cả cookies có sẵn."""
    parts = []
    for key in COOKIE_KEYS:
        value = cookies_dict.get(key)
        if value:
            parts.append(f"{key}={value}")
    return "; ".join(parts)


# ─── Core token fetch với multi-strategy ────────────────────────────────────

def _fetch_token(cookies_dict: dict, strategy_idx: int, attempt: int) -> dict:
    """
    Gửi request GraphQL với strategy cụ thể.
    """
    url, scope, user_agent, strategy_name = STRATEGIES[strategy_idx]

    time.sleep(random.uniform(0.2, 1.0))

    headers = dict(BASE_HEADERS_COMMON)
    headers["User-Agent"] = user_agent
    headers["Cookie"] = _build_cookie_header(cookies_dict)

    payload = {
        **GRAPHQL_PAYLOAD_BASE,
        "variables": scope,
    }

    log = {
        "strategy": strategy_name,
        "strategy_idx": strategy_idx,
        "url": url,
        "status": None,
        "len": 0,
        "preview": "",
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
            verify=False,
        )
        log["status"] = resp.status_code
        log["len"] = len(resp.text or "")
        log["preview"] = (resp.text or "")[:800]
    except requests.RequestException as e:
        log["status"] = "ERR"
        log["preview"] = str(e)[:300]
        return {"log": log, "token": None, "expires": None}

    if resp.status_code != 200:
        return {"log": log, "token": None, "expires": None}

    try:
        data = resp.json()
    except Exception:
        return {"log": log, "token": None, "expires": None}

    token = None
    expires = None

    if isinstance(data, dict):
        payload_data = data.get("data")
        if isinstance(payload_data, dict):
            token = payload_data.get("createAutoLoginToken")
        if not token:
            try:
                tm = re.search(r'"createAutoLoginToken"\s*:\s*"([^"]+)"', resp.text)
                if tm:
                    token = tm.group(1)
            except Exception:
                pass

    return {"log": log, "token": token, "expires": expires}


# ─── Main generation function ────────────────────────────────────────────────

def get_login_links(cookies_dict: dict) -> dict:
    """
    Lấy login link từ cookies.
    Thử tất cả strategies để tối đa khả năng thành công.
    """
    if not cookies_dict.get("NetflixId"):
        return {"ok": False, "error": "Thiếu cookie: NetflixId"}

    if not cookies_dict.get("SecureNetflixId"):
        return {"ok": False, "error": "Thiếu cookie: SecureNetflixId"}

    # Nếu thiếu nfvdid, vẫn thử — nhiều cookie vẫn chạy được
    missing_nfvdid = not cookies_dict.get("nfvdid")

    all_debug = []
    error_hints = []

    # Thử mỗi strategy
    for sidx in range(len(STRATEGIES)):
        strategy_name = STRATEGIES[sidx][3]

        for attempt in range(1, 3):
            result = _fetch_token(cookies_dict, sidx, attempt)
            all_debug.append(result["log"])

            if result["token"]:
                return {
                    **_build_result(result["token"], result["expires"], strategy_name),
                    "debug": all_debug,
                }

            # Phân tích lỗi
            preview = result["log"].get("preview", "")
            status = result["log"].get("status")

            if status == 200 and "PERMISSION_DENIED" in preview:
                error_hints.append(f"Strategy {strategy_name}: PERMISSION_DENIED")
                break  # strategy này không work, chuyển strategy khác
            elif status == 200 and "DetailedAccessDeniedException" in preview:
                error_hints.append(f"Strategy {strategy_name}: AccessDeniedException")
                break
            elif status == 200 and "data\":null" in preview:
                error_hints.append(f"Strategy {strategy_name}: data=null")
                break
            elif status == 200 and '"errors"' in preview:
                err_match = re.search(r'"message"\s*:\s*"([^"]+)"', preview)
                if err_match:
                    error_hints.append(f"Strategy {strategy_name}: {err_match.group(1)[:80]}")
                break
            elif status == "ERR":
                error_hints.append(f"Strategy {strategy_name}: connection error")
                break

            if attempt < 2:
                time.sleep(random.uniform(0.5, 1.5))

    last = all_debug[-1] if all_debug else {}

    # Xây dựng error message rõ ràng
    status = last.get("status")
    preview = last.get("preview", "")

    if missing_nfvdid:
        hint = " — Cookie không có nfvdid (có thể không cần)"
    else:
        hint = ""

    if error_hints:
        err_summary = "; ".join(error_hints[:3])
        return {
            "ok": False,
            "error": f"Tất cả strategies thất bại{hint}. Chi tiết: {err_summary}",
            "debug": all_debug,
        }

    return {
        "ok": False,
        "error": f"HTTP {status} sau {len(STRATEGIES)} strategies — cookie có thể hết hạn hoặc IP bị Netflix flag{hint}",
        "debug": all_debug,
    }


# ─── Debug probe ──────────────────────────────────────────────────────────────

def probe_endpoint(cookies_dict: dict, url: str, method: str = "POST") -> dict:
    """Test endpoint tùy ý với cookies đã cho."""
    headers = dict(BASE_HEADERS_COMMON)
    headers["User-Agent"] = STRATEGIES[0][2]
    headers["Cookie"] = _build_cookie_header(cookies_dict)

    payload = {**GRAPHQL_PAYLOAD_BASE, "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"}}

    try:
        if method.upper() == "POST":
            resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        else:
            resp = requests.get(url, headers=headers, timeout=30, verify=False)
        body_preview = (resp.text or "")[:1500]
        return {
            "status": resp.status_code,
            "body": body_preview,
            "build_id": "android/63884",
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": "createAutoLoginToken" in body_preview,
        }
    except Exception as e:
        return {
            "status": "ERR",
            "body": str(e)[:300],
            "build_id": "android/63884",
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": False,
        }
