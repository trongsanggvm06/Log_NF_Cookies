"""
Netflix Login Link Generator

Token NATIVE qua iOS FTL NFToken — path ["account","token","default"].
  Endpoint: https://ios.prod.ftl.netflix.com/iosui/user/15.48
  Logic port NGUYÊN từ bot tele (Netflix-Cookie-Checker-main/bot.py):
    - GET với NFTOKEN_QUERY_PARAMS + NFTOKEN_HEADERS cố định (ESN/guid hardcode)
    - version 15.48, gửi đầy đủ cookie
    - 1 token dùng cho CẢ PC lẫn Mobile:
        https://netflix.com/?nftoken=<token>

Lý do 1 link cho tất cả: Netflix AASA chính thức (apple-app-site-association) loại
trừ /unsupported khỏi Universal Link. Path "/* (root) thì KHÔNG bị exclude → iOS
handoff sang app Netflix, Android mở app qua App Link, web/desktop set session
cookie và redirect vào Netflix. 1 link dùng được cho cả 3 platform.

Ref: github.com/harshitkamboj/Netflix-NFToken-Generator
"""
import json
import re
import urllib.parse
from datetime import datetime, timezone

import requests
from urllib3.exceptions import InsecureRequestWarning

from config import LOGIN_BASE, USER_AGENT

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ─── Cookie keys ───────────────────────────────────────────────────────────────

COOKIE_KEYS = ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn", "gsid")

# ─── NFToken API (iOS FTL) — token NATIVE "account.token.default" ─────────────────
# Port NGUYÊN từ bot tele: version 15.48, ESN + guid hardcode, headers cố định.
# 1 token này dùng cho CẢ link PC và Mobile.
NFTOKEN_API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"

NFTOKEN_QUERY_PARAMS = {
    "appVersion": "15.48.1",
    "config": '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false","cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true","addHorizontalBoxArtToVideoSummariesEnabled":"false","skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false","baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true","postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false","roarEnabled":"false","useSeason1AltLabelEnabled":"false","disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true","kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true","contentWarningEnabled":"true","videosInPopularGamesEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}',
    "device_type": "NFAPPL-02-",
    "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom": "phone",
    "iosVersion": "15.8.5",
    "isTablet": "false",
    "languages": "en-US",
    "locale": "en-US",
    "maxDeviceWidth": "375",
    "model": "saget",
    "modelType": "IPHONE8-1",
    "odpAware": "true",
    "path": '["account","token","default"]',
    "pathFormat": "graph",
    "pixelDensity": "2.0",
    "progressive": "false",
    "responseFormat": "json",
}

NFTOKEN_HEADERS = {
    "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.attempt": "1",
    "x-netflix.request.client.user.guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.context.profile-guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.context.app-version": "15.48.1",
    "x-netflix.argo.translated": "true",
    "x-netflix.context.form-factor": "phone",
    "x-netflix.context.sdk-version": "2012.4",
    "x-netflix.client.appversion": "15.48.1",
    "x-netflix.client.type": "argo",
    "x-netflix.client.ftl.esn": "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.context.locales": "en-US",
    "accept-language": "en-US;q=1",
    "x-netflix.context.os-version": "15.8.5",
    "x-netflix.request.client.context": '{"appState":"foreground"}',
    "x-netflix.context.ui-flavor": "argo",
}


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
    - Mỗi dòng 1 account: raw "key=...; NetflixId=..." HOẶC 1 JSON array/dòng — KỂ CẢ trộn lẫn
    - JSON arrays (kể cả khi 1 array trải nhiều dòng)
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

    # 2. Mỗi dòng là 1 account HOÀN CHỈNH — raw "nfvdid=...; NetflixId=..." HOẶC 1 JSON array/dòng,
    #    KỂ CẢ khi TRỘN lẫn 2 kiểu trong cùng input. Điều kiện: ≥2 dòng và MỖI dòng tự parse ra
    #    được NetflixId của riêng nó.
    #    PHẢI check TRƯỚC bước gom JSON array (step 3): nếu không, các dòng raw bị bỏ sót — chỉ
    #    nhận JSON array → "paste 4 ra 2". Cũng tránh tách theo vị trí NetflixId= gây lệch chéo cookie.
    nonempty_lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(nonempty_lines) >= 2 and all(
        parse_cookies(ln).get("NetflixId") for ln in nonempty_lines
    ):
        return nonempty_lines

    # 3. Multiple JSON arrays
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

    # 4. Split bằng dòng trắng lớn (phòng batch multi-line: mỗi block trải nhiều dòng)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs

    # 5. Dòng bắt đầu bằng SecureNetflixId= HOẶC NetflixId= → mỗi dòng là 1 block
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

    # 6. Raw: anchor NetflixId= hoặc SecureNetflixId= ở đầu dòng / sau \n
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

    # 7. Nhiều NetflixId= trong text
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

    # 8. Fallback: 1 block
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
                and name not in cookie_dict):
            # Trước đây bỏ qua value rỗng → cookie flwssn/nfvdid bị mất.
            # Netflix vẫn nhận cookie với value="" (rdr track ID) — phải giữ.
            # Riêng NetflixId/SecureNetflixId nếu rỗng thì bỏ (vô nghĩa, sẽ fail ở NFToken).
            if not value and name in ("NetflixId", "SecureNetflixId"):
                return
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


def _build_result(token: str, expiry, method_name: str) -> dict:
    url = LOGIN_BASE + token
    return {
        "ok": True,
        "token": token,   # raw token — app.py dùng để build link mobile /go (tránh app cướp link)
        "url": url,
        "pc": url,
        # mobile mặc định = link netflix; app.py sẽ ghi đè bằng URL /go (landing page) khi có request context
        "mobile": url,
        "expiry": _fmt_expiry(expiry),
        "build_id": method_name,
        "strategy": method_name,
    }


def _build_cookie_header(cookies_dict: dict) -> str:
    """
    Build cookie header gửi cho Netflix.
    Gửi đúng dạng TRÌNH DUYỆT lưu = URL-encoded (NetflixId/SecureNetflixId chứa = & .).
    parse_cookies đã decode value → ở đây encode lại để khớp dạng gốc (giống cookie
    bot gửi qua requests.Session).
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


# ─── NFToken (port từ bot tele create_nftoken) ────────────────────────────────

def create_nftoken(cookies_dict: dict, attempts: int = 3) -> tuple:
    """
    Lấy token NATIVE qua iOS FTL account.token.default — logic giống hệt bot tele.
    Trả về (token_data | None, error | None, logs).
    """
    if not cookies_dict.get("NetflixId"):
        return None, "Không tìm thấy NetflixId trong cookie", []

    cookie_header = _build_cookie_header(cookies_dict)
    logs = []
    last_error = "NFToken API error"

    for attempt in range(1, attempts + 1):
        log = {"method": f"NFToken iosui/15.48 (try {attempt})",
               "url": NFTOKEN_API_URL, "status": None, "preview": ""}
        try:
            headers = dict(NFTOKEN_HEADERS)
            headers["Cookie"] = cookie_header
            resp = requests.get(
                NFTOKEN_API_URL,
                params=NFTOKEN_QUERY_PARAMS,
                headers=headers,
                timeout=30,
                verify=False,
            )
            log["status"] = resp.status_code
            log["preview"] = (resp.text or "")[:300]
            logs.append(log)

            if resp.status_code == 403:
                last_error = "403 Forbidden — cookie có thể đã hết hạn hoặc bị chặn"
                continue
            if resp.status_code == 429:
                last_error = "429 Rate Limited — thử lại sau"
                continue
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code} error"
                continue

            try:
                data = resp.json()
            except Exception:
                data = None

            token = None
            expires = None
            if isinstance(data, dict):
                token_data = (
                    (((data.get("value") or {}).get("account") or {}).get("token") or {}).get("default")
                    or {}
                )
                token = token_data.get("token")
                expires = token_data.get("expires")
            if not token:
                m = re.search(r'"token"\s*:\s*"([^"]+)"', resp.text or "")
                if m:
                    token = m.group(1)

            if token:
                return {"token": token, "expires": expires}, None, logs

            # HTTP 200 nhưng value rỗng {} → Netflix NHẬN request nhưng KHÔNG cấp token cho
            # account này (từ chối mềm). Hay gặp với cookie "sống" trên web nhưng luồng token
            # iOS FTL từ chối, hoặc account đã đăng xuất/đổi mật khẩu phía server.
            if isinstance(data, dict) and not (data.get("value") or {}):
                last_error = ("Netflix không cấp token (HTTP 200, value rỗng) — account bị từ chối "
                              "Cookies Hỏng")
            else:
                last_error = "Token không có trong response (cookie có thể đã hết hạn)"

        except requests.exceptions.Timeout:
            last_error = f"Timeout (attempt {attempt}/{attempts})"
            log["status"] = "ERR"
            log["preview"] = last_error
            logs.append(log)
        except requests.exceptions.RequestException as e:
            last_error = f"Network error: {e}"
            log["status"] = "ERR"
            log["preview"] = str(e)[:200]
            logs.append(log)
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            log["status"] = "ERR"
            log["preview"] = str(e)[:200]
            logs.append(log)

    # ─── Fallback D: thử endpoint phụ nếu FTL từ chối ─────────────────────────────
    # Thử loginWithToken với token = "auto" (Netflix endpoint tự cấp) — đôi khi cookie
    # "sống" nhưng iOS FTL từ chối do path-specific, trong khi web path vẫn cấp token.
    fb_token, fb_log = _fallback_create_token(cookies_dict)
    if fb_token:
        logs.append(fb_log)
        return fb_token, None, logs
    if fb_log:
        logs.append(fb_log)

    return None, last_error, logs


def _fallback_create_token(cookies_dict: dict) -> tuple:
    """
    Fallback khi FTL từ chối: thử 1 endpoint phụ.
    Trả về ({token, expires} | None, log_dict | None).
    """
    cookie_header = _build_cookie_header(cookies_dict)
    headers = {
        "User-Agent": NFTOKEN_HEADERS["User-Agent"],
        "x-netflix.request.client.user.guid":
            NFTOKEN_HEADERS["x-netflix.request.client.user.guid"],
        "x-netflix.context.app-version":
            NFTOKEN_HEADERS["x-netflix.context.app-version"],
        "Cookie": cookie_header,
    }
    # Endpoint web account token (path mới) — Netflix thường trả token ngay cả khi
    # FTL iOS từ chối với cùng cookie.
    urls = [
        "https://www.netflix.com/api/shakti/v1db76858/createAutoLoginToken",
        "https://www.netflix.com/api/shakti/1b8b10944f/createAutoLoginToken",
    ]
    for url in urls:
        try:
            resp = requests.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                data='{}',
                timeout=20,
                verify=False,
            )
            if resp.status_code == 200:
                data = {}
                try:
                    data = resp.json()
                except Exception:
                    pass
                token = None
                if isinstance(data, dict):
                    token = (
                        data.get("token")
                        or data.get("nftoken")
                        or (data.get("value") or {}).get("token")
                    )
                if not token:
                    m = re.search(r'"(?:token|nftoken)"\s*:\s*"([^"]+)"', resp.text or "")
                    if m:
                        token = m.group(1)
                if token:
                    return {"token": token, "expires": None}, {
                        "method": "fallback createAutoLoginToken",
                        "url": url,
                        "status": resp.status_code,
                        "preview": "ok (fallback)",
                    }
        except Exception as e:
            return None, {
                "method": "fallback createAutoLoginToken",
                "url": url,
                "status": "ERR",
                "preview": str(e)[:200],
            }
    return None, None


# ─── Main generation function ────────────────────────────────────────────────

def get_login_links(cookies_dict: dict) -> dict:
    """
    Tạo 1 login link dùng được cho cả PC, Android, iOS:
        https://netflix.com/?nftoken=<token>

    - PC/Desktop: mở trong trình duyệt → Netflix web set session → auto login.
    - iOS: click/paste vào Safari → Universal Link handoff sang app Netflix → auto login.
    - Android: click/paste vào Chrome → App Link mở app Netflix → auto login.
    Token có hiệu lực ~1 giờ, không bị bind IP/region/device.
    """
    if not cookies_dict.get("NetflixId"):
        return {"ok": False, "error": "Thiếu cookie: NetflixId"}

    token_data, error, logs = create_nftoken(cookies_dict, attempts=3)

    if error or not token_data:
        return {
            "ok": False,
            "error": error or "Cookies die (NFToken không cấp token)",
            "debug": logs,
        }

    token = token_data["token"]
    expiry = token_data.get("expires")
    method = "iOS FTL NFToken 15.48 (native)"

    return {**_build_result(token, expiry, method), "debug": logs}


# ─── Debug probe ──────────────────────────────────────────────────────────────

def probe_endpoint(cookies_dict: dict, url: str, method: str = "POST") -> dict:
    """Test endpoint tùy ý với cookies đã cho (dùng header NFToken + cookie)."""
    headers = dict(NFTOKEN_HEADERS)
    headers["Cookie"] = _build_cookie_header(cookies_dict)

    try:
        if method.upper() == "POST":
            resp = requests.post(url, headers=headers, timeout=30, verify=False)
        else:
            resp = requests.get(url, headers=headers, timeout=30, verify=False)
        body_preview = (resp.text or "")[:1500]
        return {
            "status": resp.status_code,
            "body": body_preview,
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": ('"token"' in body_preview) or ("createAutoLoginToken" in body_preview),
        }
    except Exception as e:
        return {
            "status": "ERR",
            "body": str(e)[:300],
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": False,
        }


# ─── Server-side redeem (gọi từ /redeem trong app.py) ────────────────────────
# Lý do cần: NFToken do server Render sinh ra, redeem từ IP khác (mobile user) có thể
# Netflix từ chối → 404 trong app. Redeem lại từ IP server (đúng IP phát sinh token)
# sẽ pass; cookie session Netflix sẽ được set vào response, client set vào browser
# rồi mở netflix.com → login ok cả web lẫn app (app tự đọc cookie NetflixId).

REDEEM_HEADERS_BASE = {
    "User-Agent": USER_AGENT,
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8",
    "origin": "https://www.netflix.com",
    "referer": "https://www.netflix.com/",
    "x-netflix.request.client.user.guid": NFTOKEN_HEADERS.get(
        "x-netflix.request.client.user.guid", "A4CS633D7VCBPE2GPK2HL4EKOE"
    ),
    "x-netflix.context.app-version": NFTOKEN_HEADERS.get(
        "x-netflix.context.app-version", "15.48.1"
    ),
}

# Một số buildId Netflix hay dùng (lấy từ web HTML hiện tại; fallback nếu /loginWithToken 404)
NETFLIX_BUILDS = [
    "1b8b10944f",
    "v1db76858",
    "v1f0c5e3f",
    "v1234567",
]


def _server_redeem_nftoken(token: str) -> dict:
    """
    Server-side redeem NFToken: gọi Netflix login API từ IP server.

    Trả về dict:
      ok: bool
      redirect: URL netflix client nên mở (thường https://www.netflix.com/browse)
      set_cookies: list[{name, value, domain, path, expires}] — Netflix session cookie
        client sẽ set thủ công vào document.cookie để web/app login.
      message: thông báo thân thiện
    """
    last_err = "redeem failed"
    token_safe = urllib.parse.quote(token, safe="")
    nf_token_url = "https://www.netflix.com/?nftoken=" + token_safe
    # Lưu ý: redirect trỏ tới `?nftoken=...` (KHÔNG phải /browse) vì AASA của
    # netflix.com cấu hình pattern /?* (bất kỳ path / có query) — iOS/Android
    # sẽ mở app Netflix qua Universal Link/App Link thay vì Safari. App Netflix
    # tự parse nftoken từ URL và redeem thành session trong app → auto login.
    # Trên desktop/browser, Netflix web cũng parse ?nftoken= để set session.
    for build_id in NETFLIX_BUILDS:
        url = f"https://www.netflix.com/api/shakti/{build_id}/loginWithToken"
        headers = dict(REDEEM_HEADERS_BASE)
        headers["content-type"] = "application/json"
        # Body Netflix hay dùng: {"token": "<nftoken>"} hoặc query string.
        # Endpoint loginWithToken chấp nhận cả 2.
        try:
            # Body JSON dùng concat thường (KHÔNG dùng str.format vì token Netflix có thể
            # chứa ký tự '{' hoặc '}' → str.format throw KeyError/IndexError).
            safe_token = token.replace("\\", "\\\\").replace('"', '\\"')
            body_json = '{"token":"' + safe_token + '"}'
            resp = requests.post(
                url,
                headers=headers,
                params={"token": token},
                data=body_json,
                timeout=20,
                verify=False,
            )
        except requests.exceptions.RequestException as e:
            last_err = f"network: {e}"
            continue

        if resp.status_code == 200:
            # Đọc Set-Cookie từ response
            set_cookies_raw = resp.headers.get("set-cookie", "") or ""
            cookies_out = _parse_set_cookie(set_cookies_raw)
            # Nếu response có body chứa session/user info → ok
            try:
                data = resp.json()
            except Exception:
                data = {}
            user = (
                data.get("user") or {}
            ) if isinstance(data, dict) else {}
            if user and not cookies_out:
                last_err = "200 nhưng không có session cookie"
                continue
            return {
                "ok": True,
                "redirect": nf_token_url,
                "set_cookies": cookies_out,
                "user": (user.get("email") if isinstance(user, dict) else None),
                "build_id": build_id,
                "message": "Redeem thành công — đang mở Netflix…",
            }
        last_err = f"HTTP {resp.status_code} (build {build_id})"
    # Fallback cuối: trả URL /?nftoken=… để client tự redeem từ browser.
    # iOS/Android sẽ mở app Netflix qua Universal Link vì AASA match /?*.
    return {
        "ok": False,
        "redirect": nf_token_url,
        "error": last_err,
        "fallback": True,
        "message": "Server không redeem được NFToken — sẽ thử mở trực tiếp netflix.com",
    }


def _parse_set_cookie(raw: str) -> list:
    """
    Parse raw Set-Cookie header thành list[{name, value, domain, path, expires, ...}].

    KHÔNG dùng regex split vì Set-Cookie có Expires chứa dấu phẩy vd
    "Expires=Wed, 21 Oct 2026 07:28:00 GMT" → split nhầm thành nhiều cookie.

    Cách an toàn: dùng http.cookiejar.extract_cookies để parse từng response.
    """
    if not raw:
        return []

    # Tạo response giả để http.cookiejar xử lý đúng chuẩn RFC 6265.
    from http.cookiejar import DefaultCookiePolicy
    try:
        from http.cookiejar import Cookie, CookieJar
    except ImportError:
        return []

    # requests có thể trả raw string nhiều cookie ngăn bởi ", ". Mỗi cookie có
    # format "name=value; attr1=val1; attr2; ...". Expires bên trong có dấu ", "
    # nhưng CookieJar chấp nhận cả string multi-cookie qua CookieJar.make_cookies.
    jar = CookieJar(policy=DefaultCookiePolicy())
    # Tạo response object giả
    from urllib.request import Request as _Req
    from http.client import HTTPResponse as _HResp
    # Đơn giản hơn: dùng http.cookies.SimpleCookie thử cho từng đoạn sau khi
    # tách bằng heuristic tốt hơn.
    chunks = _safe_split_set_cookie(raw)
    out = []
    from http.cookies import SimpleCookie
    for chunk in chunks:
        try:
            sc = SimpleCookie()
            # SimpleCookie không chấp nhận Expires có dấu phẩy. Patch: thay ", " → ",,"
            # trong phần Expires trước khi parse.
            patched = _escape_expires_comma(chunk)
            sc.load(patched)
            for name, morsel in sc.items():
                out.append({
                    "name": name,
                    "value": morsel.value,
                    "domain": morsel.get("domain", ".netflix.com") or ".netflix.com",
                    "path": morsel.get("path", "/") or "/",
                    "expires": morsel.get("expires"),
                    "secure": bool(morsel.get("secure")),
                    "httpOnly": bool(morsel.get("httponly")),
                    "sameSite": morsel.get("samesite"),
                })
        except Exception:
            # Fallback cuối: parse thủ công
            try:
                head = chunk.split(";")[0]
                if "=" not in head:
                    continue
                n, _, v = head.partition("=")
                out.append({
                    "name": n.strip(),
                    "value": v.strip(),
                    "domain": ".netflix.com",
                    "path": "/",
                    "expires": None,
                    "secure": False,
                    "httpOnly": False,
                    "sameSite": None,
                })
            except Exception:
                continue
    return out


def _safe_split_set_cookie(raw: str) -> list:
    """
    Tách chuỗi nhiều Set-Cookie thành list, dựa trên vị trí ký tự ';' cuối
    của cookie trước + dấu phân cách ", " trước tên cookie mới.
    An toàn với Expires có dấu phẩy vì ta chỉ tách khi gặp
    pattern ", <cookie_name>=".
    """
    KNOWN = (
        "NetflixId", "SecureNetflixId", "profilesSessionId",
        "nfvdid", "OptanonConsent", "flwssn", "gsid",
        "SecureNetflixIdSecure", "memclid", "player_bandwidth",
        "lcv", "clSharedContext", "chasedSegmentationData",
        "edgeServerRedirectIndicator", "BUILD_INFO", "startTime",
        "JSESSIONID", "ndbc", "pas", "hasSeenCACOptIn", "cookie",
        "CONSENT", "v1st", "v1ss", "v1js", "v2st", "v2ss", "v2js",
    )
    out = []
    s = raw
    n = len(s)
    i = 0
    while i < n:
        # Bỏ qua ", " đầu tiên nếu có
        if s[i:i+2] == ", ":
            i += 2
        # Tìm tên cookie
        start = i
        # Tìm dấu "=" đầu tiên
        eq = s.find("=", i)
        if eq == -1:
            # Không còn cookie nào
            tail = s[start:].strip().lstrip(",").strip()
            if tail:
                out.append(tail)
            break
        # Tên là phần từ start đến eq
        name = s[start:eq].strip()
        # Check xem name có phải cookie name thật không
        # Tên cookie hợp lệ: không có dấu phẩy/khoảng trắng bên trong
        if not name or any(c in name for c in " ,;\"'"):
            # Không phải đầu cookie, skip 1 char
            i = start + 1
            continue
        # Tìm kết thúc cookie: ';' hoặc ', ' trước tên cookie tiếp theo
        j = eq + 1
        end = n
        while j < n:
            if s[j] == ";":
                end = j
                break
            # Nếu gặp ", " mà phía sau là tên cookie thật
            if s[j:j+2] == ", ":
                # Tên cookie tiếp theo?
                rest = s[j+2:]
                next_eq = rest.find("=")
                if next_eq > 0:
                    next_name = rest[:next_eq].strip()
                    if next_name and all(c not in next_name for c in " ,;\"'"):
                        # OK, đây là boundary giữa 2 cookie
                        end = j
                        break
            j += 1
        cookie_str = s[start:end].strip()
        if cookie_str:
            out.append(cookie_str)
        i = end
    return out


def _escape_expires_comma(cookie_str: str) -> str:
    """
    SimpleCookie không chấp nhận dấu phẩy trong Expires. Tạm thời thay ", " → ",,"
    trong phần Expires, SimpleCookie sẽ parse thành 1 token dài (chấp nhận được,
    vì client chỉ cần tên cookie, không cần expires chính xác).
    """
    m = re.search(r"(expires=[^;]+)", cookie_str, re.IGNORECASE)
    if not m:
        return cookie_str
    expires_part = m.group(1)
    fixed = expires_part.replace(", ", ",,")
    return cookie_str.replace(expires_part, fixed)
