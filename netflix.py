"""
Netflix Login Link Generator

Token NATIVE (CHÍNH): iOS FTL Falcor — path ["account","token","default"].
  Endpoint: https://ios.prod.ftl.netflix.com/iosui/user/<version>
  → token mà APP NETFLIX NATIVE chấp nhận auto-login (giống @nf_getlink_bot):
    mở app → load vài giây → vào thẳng chọn profile.

Token WEBVIEW (FALLBACK): GraphQL createAutoLoginToken (scope WEBVIEW_MOBILE_STREAMING).
  → CHỈ redeem được trên trình duyệt web; app native sẽ hiện màn đăng nhập.

Ref: github.com/harshitkamboj/Netflix-NFToken-Generator
"""
import json
import re
import random
import string
import time
import uuid
import urllib.parse
from datetime import datetime, timezone

import requests
from urllib3.exceptions import InsecureRequestWarning

from config import PC_LOGIN_BASE, MOBILE_LOGIN_BASE

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ─── Cookie keys ───────────────────────────────────────────────────────────────

COOKIE_KEYS = ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn", "gsid")

# ─── GraphQL (FALLBACK — token webview, chỉ web redeem được) ─────────────────────

# Strategy = (graphql_url, scope, user_agent, description)
STRATEGIES = [
    (
        "https://android13.prod.ftl.netflix.com/graphql",
        {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
        "GraphQL WEBVIEW_MOBILE_STREAMING",
    ),
    (
        "https://web.prod.ftl.netflix.com/graphql",
        {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)",
        "GraphQL web.prod WEBVIEW_MOBILE_STREAMING",
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

# ─── iOS FTL (Falcor) — token NATIVE "account.token.default" ─────────────────────
# Đây là token mà app Netflix native auto-login được (giống @nf_getlink_bot).
# Thử lần lượt nhiều version; version nào còn sống thì dùng.
FTL_VERSIONS = ("18.0", "17.0", "16.0", "15.48")

_FTL_CONFIG_BLOB = (
    '{"gamesInTrailersEnabled":"false","kidsBillboardEnabled":"true",'
    '"baselineOnIpadEnabled":"true","postPlayPreviewsEnabled":"false","roarEnabled":"false",'
    '"kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true",'
    '"contentWarningEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}'
)


# ─── Cookie parser ────────────────────────────────────────────────────────────

def _decode_cookie_value(value: str) -> str:
    if isinstance(value, str) and "%" in value:
        try:
            return urllib.parse.unquote(value)
        except Exception:
            return value
    return value


def _strip_quotes(value: str) -> str:
    """Bỏ cặp nháy bao quanh value nếu có: \"v=3...\" -> v=3..."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
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
    lines = text.split("\n")
    line_blocks = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
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

    # 5. Raw: anchor NetflixId= hoặc SecureNetflixId= ở đầu dòng / sau \n
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
    """Quét toàn batch tìm nfvdid; gán cho block thiếu."""
    if not block_dicts:
        return block_dicts

    all_nfvdids = []
    for cd in block_dicts:
        if cd.get("nfvdid"):
            all_nfvdids.append(cd["nfvdid"])

    if not all_nfvdids:
        return block_dicts

    for cd in block_dicts:
        if not cd.get("nfvdid") and all_nfvdids:
            cd["nfvdid"] = all_nfvdids[0]

    return block_dicts


def parse_cookies(raw: str) -> dict:
    """
    Parse cookie string thành dict — hỗ trợ MỌI format Netflix phổ biến:
      • JSON array (Cookie-Editor / EditThisCookie) — kể cả khi name/value KHÔNG liền nhau
      • JSON object {NetflixId: ...} hoặc {"cookies": [...]}
      • Chuỗi header: NetflixId=...; SecureNetflixId=...
      • Raw key=value mỗi dòng
      • Netscape cookies.txt (TAB-separated — từ tiện ích "Get cookies.txt")
      • name: value (dấu hai chấm)
      • JSON hỏng / cắt dở (vẫn vớt được name+value)
      • Giá trị có/không URL-encode, có/không bọc nháy
    """
    text = raw.strip()
    cookie_dict: dict = {}

    def _take(name, value):
        if (name in COOKIE_KEYS and isinstance(value, str)
                and value and name not in cookie_dict):
            cookie_dict[name] = _decode_cookie_value(value)

    def _from_objects(items):
        for c in items:
            if not isinstance(c, dict):
                continue
            name = c.get("name") or c.get("Name") or c.get("key") or c.get("Key")
            value = c.get("value")
            if value is None:
                value = c.get("Value")
            _take(name, value)

    # 1) JSON hợp lệ ──────────────────────────────────────────────────
    data = None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    if isinstance(data, list):
        _from_objects(data)
    elif isinstance(data, dict):
        if isinstance(data.get("cookies"), list):
            _from_objects(data["cookies"])
        for key in COOKIE_KEYS:
            v = data.get(key)
            if isinstance(v, str):
                _take(key, v)

    # 2) JSON-fragment (JSON hỏng / cắt dở / name-value không liền nhau):
    if not all(k in cookie_dict for k in ("NetflixId", "SecureNetflixId", "nfvdid")):
        for obj in re.findall(r"\{[^{}]*\}", text):
            nm = re.search(r'"name"\s*:\s*"([^"]+)"', obj, re.IGNORECASE)
            vl = re.search(r'"value"\s*:\s*"([^"]*)"', obj, re.IGNORECASE)
            if nm and vl:
                _take(nm.group(1), vl.group(1))
        for key in COOKIE_KEYS:
            if key in cookie_dict:
                continue
            nm = re.search(rf'"name"\s*:\s*"{re.escape(key)}"', text, re.IGNORECASE)
            if not nm:
                continue
            vm = re.search(r'"value"\s*:\s*"([^"]*)"',
                           text[nm.end():nm.end() + 500], re.IGNORECASE)
            if not vm:
                befs = list(re.finditer(r'"value"\s*:\s*"([^"]*)"',
                                        text[max(0, nm.start() - 500):nm.start()],
                                        re.IGNORECASE))
                vm = befs[-1] if befs else None
            if vm:
                _take(key, vm.group(1))

    # 3) Chuỗi thô — tách name/value bằng '='  |  ':'  |  TAB (Netscape):
    for key in COOKIE_KEYS:
        if key in cookie_dict:
            continue
        m = re.search(
            rf"(?<!\w){re.escape(key)}[ ]*[=:\t][ ]*"
            rf"(?:\"([^\"]*)\"|'([^']*)'|([^;,\s\"']+))",
            text,
        )
        if m:
            val = m.group(1) or m.group(2) or m.group(3)
            if val:
                cookie_dict[key] = _decode_cookie_value(_strip_quotes(val))

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


def _build_result(pc_token: str, mobile_token: str, expiry, method_name: str) -> dict:
    return {
        "ok": True,
        "pc": PC_LOGIN_BASE + pc_token,         # web: token webview (đã xác nhận chạy web)
        "mobile": MOBILE_LOGIN_BASE + mobile_token,  # app: token native (auto-login như bot)
        "expiry": _fmt_expiry(expiry),
        "build_id": method_name,
        "strategy": method_name,
    }


def _build_cookie_header(cookies_dict: dict) -> str:
    """
    Build cookie header gửi cho Netflix.
    Gửi đúng dạng TRÌNH DUYỆT lưu = URL-encoded (NetflixId/SecureNetflixId chứa = & .).
    parse_cookies đã decode value → ở đây encode lại để khớp dạng gốc.
    """
    parts = []
    for key in COOKIE_KEYS:
        value = cookies_dict.get(key)
        if not value:
            continue
        if "%" not in value:  # value đã decode → encode lại về dạng browser gửi
            value = urllib.parse.quote(value, safe="-_.~")
        parts.append(f"{key}={value}")
    return "; ".join(parts)


# ─── Token NATIVE qua iOS FTL (account.token.default) ────────────────────────

def _gen_esn() -> str:
    """ESN random mỗi request — hardcode ESN sẽ bị Netflix flag (403)."""
    chars = string.digits + string.ascii_uppercase
    return "NFAPPL-02-IPHONE8=1-PXA-" + "".join(random.choice(chars) for _ in range(128))


def _ftl_params(version: str, esn: str) -> dict:
    return {
        "appVersion": f"{version}.1", "config": _FTL_CONFIG_BLOB, "device_type": "NFAPPL-02-",
        "esn": esn, "idiom": "phone", "iosVersion": "18.5", "isTablet": "false",
        "languages": "en-US", "locale": "en-US", "maxDeviceWidth": "375", "model": "saget",
        "modelType": "IPHONE8-1", "odpAware": "true",
        "path": '["account","token","default"]', "pathFormat": "graph",
        "progressive": "false", "responseFormat": "json",
    }


def _ftl_headers(version: str, esn: str, cookie_header: str) -> dict:
    return {
        "User-Agent": f"Argo/{version}.1 (iPhone; iOS 18.5; Scale/2.00)",
        "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~' + version + '.0/user","control_tag":"iosui_argo"}',
        "x-netflix.context.app-version": f"{version}.1",
        "x-netflix.argo.translated": "true",
        "x-netflix.context.form-factor": "phone",
        "x-netflix.client.appversion": f"{version}.1",
        "x-netflix.client.type": "argo",
        "x-netflix.client.ftl.esn": esn,
        "x-netflix.context.locales": "en-US",
        "x-netflix.context.top-level-uuid": str(uuid.uuid4()).upper(),
        "x-netflix.client.iosversion": "18.5",
        "x-netflix.context.os-version": "18.5",
        "x-netflix.context.ui-flavor": "argo",
        "x-netflix.client.brand": "Apple",
        "x-netflix.client.model": "iPhone",
        "Cookie": cookie_header,
    }


def _fetch_token_ftl(cookies_dict: dict) -> dict:
    """Lấy token NATIVE qua iOS FTL account.token.default. Thử nhiều version."""
    cookie_header = _build_cookie_header(cookies_dict)
    logs = []
    for version in FTL_VERSIONS:
        time.sleep(random.uniform(0.2, 0.6))
        esn = _gen_esn()
        url = f"https://ios.prod.ftl.netflix.com/iosui/user/{version}"
        log = {"method": f"FTL iosui/{version}", "url": url, "status": None, "preview": ""}
        try:
            resp = requests.get(url, params=_ftl_params(version, esn),
                                headers=_ftl_headers(version, esn, cookie_header),
                                timeout=20, verify=False)
            log["status"] = resp.status_code
            log["preview"] = (resp.text or "")[:300]
        except requests.RequestException as e:
            log["status"] = "ERR"
            log["preview"] = str(e)[:200]
            logs.append(log)
            continue

        logs.append(log)
        if resp.status_code != 200:
            continue
        try:
            data = resp.json()
        except Exception:
            data = None

        token = None
        expires = None
        if isinstance(data, dict):
            try:
                tk = (((data.get("value") or {}).get("account") or {}).get("token") or {}).get("default") or {}
                token = tk.get("token")
                expires = tk.get("expires")
            except Exception:
                token = None
        if not token:
            m = re.search(r'"token"\s*:\s*"([^"]+)"', resp.text or "")
            if m:
                token = m.group(1)
        if token:
            return {"token": token, "expires": expires, "logs": logs,
                    "method": f"iOS FTL native (iosui/{version})"}
    return {"token": None, "expires": None, "logs": logs, "method": None}


# ─── GraphQL fallback (token webview) ────────────────────────────────────────

def _fetch_token(cookies_dict: dict, strategy_idx: int) -> dict:
    """Gửi request GraphQL createAutoLoginToken (token webview — fallback)."""
    url, scope, user_agent, strategy_name = STRATEGIES[strategy_idx]

    time.sleep(random.uniform(0.2, 0.8))

    headers = dict(BASE_HEADERS_COMMON)
    headers["User-Agent"] = user_agent
    headers["Cookie"] = _build_cookie_header(cookies_dict)

    payload = {**GRAPHQL_PAYLOAD_BASE, "variables": scope}

    log = {"method": strategy_name, "url": url, "status": None, "preview": ""}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        log["status"] = resp.status_code
        log["preview"] = (resp.text or "")[:300]
    except requests.RequestException as e:
        log["status"] = "ERR"
        log["preview"] = str(e)[:200]
        return {"log": log, "token": None, "expires": None}

    if resp.status_code != 200:
        return {"log": log, "token": None, "expires": None}

    try:
        data = resp.json()
    except Exception:
        data = None

    token = None
    if isinstance(data, dict):
        payload_data = data.get("data")
        if isinstance(payload_data, dict):
            token = payload_data.get("createAutoLoginToken")
    if not token:
        m = re.search(r'"createAutoLoginToken"\s*:\s*"([^"]+)"', resp.text or "")
        if m:
            token = m.group(1)

    return {"log": log, "token": token, "expires": None}


# ─── Main generation function ────────────────────────────────────────────────

def get_login_links(cookies_dict: dict) -> dict:
    """
    Tạo login link từ cookies (DUAL-TOKEN):
      • Mobile link → token NATIVE (iOS FTL account.token.default) → app auto-login như @nf_getlink_bot.
      • PC link     → token WEBVIEW (GraphQL createAutoLoginToken)  → đã xác nhận redeem trên web.
    Lấy được token nào dùng token đó; thiếu loại nào thì lấp bằng loại kia.
    """
    if not cookies_dict.get("NetflixId"):
        return {"ok": False, "error": "Thiếu cookie: NetflixId"}

    all_debug = []

    # 1) Token NATIVE qua iOS FTL (cho MOBILE — app auto-login)
    ftl = _fetch_token_ftl(cookies_dict)
    all_debug.extend(ftl["logs"])
    native = ftl["token"]
    expiry = ftl["expires"]

    # 2) Token WEBVIEW qua GraphQL (cho PC/web)
    webview = None
    for sidx in range(len(STRATEGIES)):
        result = _fetch_token(cookies_dict, sidx)
        all_debug.append(result["log"])
        if result["token"]:
            webview = result["token"]
            break
        if result["log"].get("status") == "ERR":
            break  # lỗi mạng → khỏi spam strategy còn lại

    if not native and not webview:
        return {
            "ok": False,
            "error": "Cookies die (FTL native + GraphQL đều không cấp token)",
            "debug": all_debug,
        }

    pc_token = webview or native        # web: ưu tiên webview (đã xác nhận); thiếu thì dùng native
    mobile_token = native or webview    # app: bắt buộc native; thiếu thì đành webview
    if native and webview:
        method = "FTL native (mobile) + GraphQL webview (pc)"
    elif native:
        method = "FTL native (cả 2 link)"
    else:
        method = "GraphQL webview (web-only — app native sẽ hiện login)"

    return {**_build_result(pc_token, mobile_token, expiry, method), "debug": all_debug}


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
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": ("createAutoLoginToken" in body_preview) or ('"token"' in body_preview),
        }
    except Exception as e:
        return {
            "status": "ERR",
            "body": str(e)[:300],
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": False,
        }
