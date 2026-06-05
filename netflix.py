"""
Netflix Login Link Generator

Sử dụng Netflix Android GraphQL endpoint để tạo auto-login token.
Endpoint: https://android13.prod.ftl.netflix.com/graphql
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

# ─── GraphQL Endpoint (Android) ─────────────────────────────────────────────────

GRAPHQL_URL = "https://android13.prod.ftl.netflix.com/graphql"

# GraphQL mutation payload với persisted query
GRAPHQL_PAYLOAD = {
    "operationName": "CreateAutoLoginToken",
    "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
    "extensions": {
        "persistedQuery": {
            "version": 102,
            "id": "76e97129-f4b5-41a0-a73c-12e674896849",
        }
    },
}

# Headers cần thiết cho request
BASE_HEADERS = {
    "User-Agent": "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
    "Accept": "multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.netflix.com",
    "Referer": "https://www.netflix.com/",
}

COOKIE_KEYS = ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn")


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
    Tách input thành nhiều block cookie. Tự động detect các kiểu phân cách.
    """
    text = raw.strip()
    if not text:
        return []

    # 1. ---- separator
    if "----" in text:
        return [b.strip() for b in text.split("----") if b.strip()]

    # 2. Detect multiple JSON arrays bằng bracket matching
    blocks = []
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if in_string:
            if c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
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

    # 3. Raw cookie string: mỗi cặp NetflixId + SecureNetflixId là 1 block.
    # Nếu có nfvdid xuất hiện sau cặp đó, gộp luôn vào block tương ứng.
    pair_pattern = re.compile(
        r"NetflixId=[^;\n]+;\s*SecureNetflixId=[^;\n]+;(?:\s*nfvdid=[^;\n]+;?)?",
        re.IGNORECASE,
    )
    pair_blocks = [m.group(0).strip() for m in pair_pattern.finditer(text)]
    if len(pair_blocks) >= 2:
        return pair_blocks

    # 4. Raw cookie string: nhiều "NetflixId=" trong text
    netflix_id_positions = [m.start() for m in re.finditer(r"\bNetflixId=", text)]
    if len(netflix_id_positions) >= 2:
        raw_blocks = []
        for i, start in enumerate(netflix_id_positions):
            end = netflix_id_positions[i + 1] if i + 1 < len(netflix_id_positions) else len(text)
            chunk = text[start:end].strip()
            if chunk:
                raw_blocks.append(chunk)
        if len(raw_blocks) >= 2:
            return raw_blocks

    # 5. Split theo dòng trắng
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs

    # 6. Fallback: 1 block duy nhất
    return [text]


def _fill_missing_shared_cookies(block_dicts: list[dict]) -> list[dict]:
    """
    Một số input raw chỉ có nfvdid ở vài block dù thực tế cả batch dùng chung device id.
    Với các block thiếu nfvdid, mượn nfvdid gần nhất trong batch để tránh false negative.
    """
    if not block_dicts:
        return block_dicts

    nearest_nfvdid = None
    for cookie_dict in reversed(block_dicts):
        if cookie_dict.get("nfvdid"):
            nearest_nfvdid = cookie_dict["nfvdid"]
        elif nearest_nfvdid:
            cookie_dict["nfvdid"] = nearest_nfvdid

    nearest_nfvdid = None
    for cookie_dict in block_dicts:
        if cookie_dict.get("nfvdid"):
            nearest_nfvdid = cookie_dict["nfvdid"]
        elif nearest_nfvdid:
            cookie_dict["nfvdid"] = nearest_nfvdid

    return block_dicts


def parse_cookies(raw: str) -> dict:
    """Hỗ trợ JSON array, JSON object, và chuỗi thuần."""
    text = raw.strip()
    cookie_dict: dict = {}

    # Thử parse JSON trước
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

    raw_patterns = {
        "NetflixId": r"(?<!\w)NetflixId=([^;,\s]+)",
        "SecureNetflixId": r"(?<!\w)SecureNetflixId=([^;,\s]+)",
        "nfvdid": r"(?<!\w)nfvdid=([A-Za-z0-9_\-]+)",
        "OptanonConsent": r"(?<!\w)OptanonConsent=([^;,\s]+)",
        "flwssn": r"(?<!\w)flwssn=([^;,\s]+)",
    }

    # Fallback: regex tìm trong chuỗi thô
    for key in COOKIE_KEYS:
        if key in cookie_dict:
            continue
        match = re.search(raw_patterns[key], text)
        if match:
            cookie_dict[key] = _decode_cookie_value(match.group(1))

    return cookie_dict


def parse_cookie_blocks(raw: str) -> list[dict]:
    """Parse toàn bộ input thành nhiều cookie dict và tự bù nfvdid gần nhất khi cần."""
    blocks = split_cookie_blocks(raw)
    parsed_blocks = [parse_cookies(block) for block in blocks]
    parsed_blocks = [cookie_dict for cookie_dict in parsed_blocks if cookie_dict]
    return _fill_missing_shared_cookies(parsed_blocks)


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


def _build_result(token: str, expiry) -> dict:
    return {
        "ok": True,
        "pc": PC_LOGIN_BASE + token,
        "mobile": MOBILE_LOGIN_BASE + token,
        "expiry": _fmt_expiry(expiry),
        "build_id": "android/63884",
    }


def _build_cookie_header(cookies_dict: dict) -> str:
    """Build cookie header với tất cả cookies có sẵn."""
    parts = []
    for key in COOKIE_KEYS:
        value = cookies_dict.get(key)
        if value:
            parts.append(f"{key}={value}")
    return "; ".join(parts)


# ─── Main request function ─────────────────────────────────────────────────────

def _fetch_token(cookies_dict: dict, attempt: int) -> dict:
    """
    Gửi request GraphQL để lấy token.
    Trả về dict với token, expiry và log info.
    """
    # Random delay để tránh Netflix detect pattern
    time.sleep(random.uniform(0.3, 1.5))

    # Build headers
    headers = dict(BASE_HEADERS)
    headers["Cookie"] = _build_cookie_header(cookies_dict)

    # Log info
    log = {
        "url": f"try{attempt}: {GRAPHQL_URL}",
        "status": None,
        "len": 0,
        "preview": "",
    }

    try:
        resp = requests.post(
            GRAPHQL_URL,
            headers=headers,
            json=GRAPHQL_PAYLOAD,
            timeout=30,
            verify=False
        )
        log["status"] = resp.status_code
        log["len"] = len(resp.text or "")
        log["preview"] = (resp.text or "")[:800]
    except requests.RequestException as e:
        log["status"] = "ERR"
        log["preview"] = str(e)[:300]
        return {"log": log, "token": None, "expires": None}

    # Parse response
    if resp.status_code != 200:
        return {"log": log, "token": None, "expires": None}

    try:
        data = resp.json()
    except Exception:
        return {"log": log, "token": None, "expires": None}

    # Extract token từ GraphQL response
    # Format: {"data": {"createAutoLoginToken": "token_value"}}
    token = None
    expires = None

    if isinstance(data, dict):
        token = data.get("data", {}).get("createAutoLoginToken")
        if not token:
            # Thử extract từ response text
            try:
                token_match = re.search(r'"createAutoLoginToken"\s*:\s*"([^"]+)"', resp.text)
                if token_match:
                    token = token_match.group(1)
            except Exception:
                pass

    return {"log": log, "token": token, "expires": expires}


# ─── Hàm chính ────────────────────────────────────────────────────────────────

def get_login_links(cookies_dict: dict) -> dict:
    """Lấy login link từ cookies."""
    # Kiểm tra cookies bắt buộc
    if not cookies_dict.get("NetflixId"):
        return {"ok": False, "error": "Thiếu cookie: NetflixId"}

    if not cookies_dict.get("SecureNetflixId"):
        return {"ok": False, "error": "Thiếu cookie: SecureNetflixId"}

    if not cookies_dict.get("nfvdid"):
        return {"ok": False, "error": "Thiếu cookie: nfvdid"}

    debug: list = []

    # Thử request nhiều lần
    for attempt in range(1, 4):
        result = _fetch_token(cookies_dict, attempt)
        debug.append(result["log"])

        if result["token"]:
            return {**_build_result(result["token"], result["expires"]), "debug": debug}

        # Nghỉ ngẫu nhiên trước khi thử lại
        if attempt < 3:
            time.sleep(random.uniform(1.0, 2.0))

    last = debug[-1]
    return {
        "ok": False,
        "error": f"HTTP {last.get('status')} sau 3 lần thử — cookie có thể đã hết hạn hoặc IP bị Netflix flag",
        "debug": debug,
    }


# ─── Debug probe ──────────────────────────────────────────────────────────────

def probe_endpoint(cookies_dict: dict, url: str, method: str = "POST") -> dict:
    """Test endpoint tùy ý với cookies đã cho."""
    headers = dict(BASE_HEADERS)
    headers["Cookie"] = _build_cookie_header(cookies_dict)

    try:
        if method.upper() == "POST":
            resp = requests.post(url, headers=headers, json=GRAPHQL_PAYLOAD, timeout=30, verify=False)
        else:
            resp = requests.get(url, headers=headers, timeout=30, verify=False)
        body_preview = (resp.text or "")[:1500]
        return {
            "status": resp.status_code,
            "body": body_preview,
            "build_id": "android/63884",
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": "createAutoLoginToken" in body_preview or "token" in body_preview.lower(),
        }
    except Exception as e:
        return {
            "status": "ERR",
            "body": str(e)[:300],
            "build_id": "android/63884",
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": False,
        }
