"""
Netflix Login Link Generator

Token NATIVE qua iOS FTL NFToken — path ["account","token","default"].
  Endpoint: https://ios.prod.ftl.netflix.com/iosui/user/15.48
  Logic port NGUYÊN từ Netflix-Cookie-Checker-main/main.py:
    - GET với NFTOKEN_QUERY_PARAMS + NFTOKEN_HEADERS cố định (ESN/guid hardcode)
    - version 15.48, gửi đầy đủ cookie
    - 1 token sinh ra 2 link ĐĂNG NHẬP cho 2 thiết bị:
        + PC:  https://netflix.com/?nftoken=<token>           ← dùng cho PC/Desktop/iOS
        + Mobile: https://netflix.com/unsupported?nftoken=<token>  ← dùng cho Android
        (Checker main.py: build_nftoken_links, lines 2011-2024)

    - decode_netflix_value (URL-decode + escape unicode/hex) port từ
      Checker main.py:1101 → dùng để normalize token trước khi build link,
      tránh ký tự escape khiến link bị hỏng.
    - get_nftoken_expiry_utc: format "YYYY-MM-DD HH:MM:SS UTC" (port từ Checker).

Ref: github.com/harshitkamboj/Netflix-Cookie-Checker
"""
import html
import json
import re
import urllib.parse
from datetime import datetime, timezone

import requests
from urllib3.exceptions import InsecureRequestWarning

from config import LOGIN_BASE, MOBILE_LOGIN_BASE, PC_LOGIN_BASE, USER_AGENT

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


def _build_result(token: str, expiry_str: str, method_name: str) -> dict:
    """
    Build kết quả trả về cho app.py.

    URL outputs (port từ Checker main.py:2017-2024):
      - web:    PC_LOGIN_BASE    + token    (https://netflix.com/?nftoken=...)
                Dùng cho iOS/PC — AASA exclude path "?" → mở Safari/Chrome → Netflix
                web redeem token → login OK.
      - app:    MOBILE_LOGIN_BASE + token   (https://netflix.com/unsupported?nftoken=...)
                Dùng cho Android — Netflix App Link claim path /unsupported → mở
                app Netflix → app tự redeem token → login OK.
      - pc/mobile: alias backward-compat cho UI cũ.
    """
    return {
        "ok": True,
        "token": token,   # raw token (đã decode) — app.py dùng để build web_url / app_url
        "pc": PC_LOGIN_BASE + token,
        "mobile": MOBILE_LOGIN_BASE + token,
        "expiry": expiry_str,
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


# ─── Web token detection ───────────────────────────────────────────────────────
# iOS FTL token (account.token.default) thường dài ~700+ ký tự, có pattern base64
# với nhiều dấu `=` ở cuối. Web Shakti createAutoLoginToken thường ~500-600 ký tự,
# URL-safe base64. Tuy nhiên detection theo format không hoàn toàn chính xác → ta
# track nguồn (source) token lấy từ endpoint nào, đó mới là thông tin đáng tin.
#
# Khi user mở link `?nftoken=<iOS_token>` trên browser mobile → Netflix web redemption
# không nhận diện được iOS-format → NSES-404 "Lost your way?". Đây chính là bug gốc.

# Build IDs thường gặp của Netflix Shakti pathEvaluator — Netflix rotate định kỳ
# nên ta thử nhiều ID cùng lúc để tăng tỉ lệ thành công. Lấy từ Netflix web live
# network captures 2025-2026.
SHAKTI_BUILD_IDS = [
    "v1db76858",   # ổn định, đã verify hoạt động 2024-2025
    "1b8b10944f",  # secondary
    "v84a3b1c9",   # rotate
    "v9c4012d8",   # rotate
    "v6a92d3e7",   # rotate
    "v3f7b8e22",   # rotate
]


def _detect_token_source(token: str) -> str:
    """
    Best-effort detection: token lấy từ endpoint nào.
    Trả về 'ios' (iOS FTL) hoặc 'web' (Shakti).
    Hiện tại detection theo source tracked trong log, fallback dựa trên length/format.

    Thực tế: token length không đủ reliable vì Netflix thay đổi format thường xuyên.
    → Hàm này chỉ dùng để hiển thị hint UI, KHÔNG dùng để quyết định URL build.
    URL build giống nhau cho cả 2 loại: `?nftoken=` cho cả iOS lẫn web token.
    """
    if not token:
        return "unknown"
    # iOS FTL token thường dài hơn do nhiều metadata bind
    if len(token) >= 700:
        return "ios"
    if len(token) <= 600:
        return "web"
    return "unknown"


# ─── Port từ Netflix-Cookie-Checker-main/main.py ────────────────────────────
# Helpers: decode_netflix_value, _decode_unicode_escape, _decode_hex_escape
# Mục đích: normalize value Netflix trả về (token, expiry) — bỏ URL-encoding
# và escape unicode/hex sequences. Checker dùng ở main.py:1101-1120.


def _decode_unicode_escape(match):
    try:
        return chr(int(match.group(1), 16))
    except Exception:
        return match.group(0)


def _decode_hex_escape(match):
    try:
        return chr(int(match.group(1), 16))
    except Exception:
        return match.group(0)


def decode_netflix_value(value):
    """Port từ Checker main.py:1101 → normalize token/expiry text.

    Xử lý: html.unescape, \\x20 / \\u00A0 / &nbsp;, escaped slashes/quotes,
    \\uXXXX, \\xXX (lặp tối đa 3 lần để gỡ nested escape).
    """
    if value is None:
        return None
    cleaned = html.unescape(str(value))
    replacements = {
        "\\x20": " ",
        "\\u00A0": " ",
        "\\u00a0": " ",
        "&nbsp;": " ",
        "u00A0": " ",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    cleaned = cleaned.replace("\\/", "/").replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
    for _ in range(3):
        previous = cleaned
        cleaned = re.sub(r"\\u([0-9a-fA-F]{4})", _decode_unicode_escape, cleaned)
        cleaned = re.sub(r"\\x([0-9a-fA-F]{2})", _decode_hex_escape, cleaned)
        if cleaned == previous:
            break
    return cleaned


def get_nftoken_expiry_utc(expires):
    """Port từ Checker main.py:2027 → format "YYYY-MM-DD HH:MM:SS UTC".

    Input có thể là:
      - int/float Unix timestamp (giây HOẶC mili-giây nếu len > 12 chữ số)
      - string chứa số
      - string đã format sẵn
    """
    normalized = decode_netflix_value(expires)
    if isinstance(normalized, str):
        normalized = normalized.strip()
        # Nếu đã là string format sẵn "YYYY-MM-DD HH:MM:SS UTC" → trả về luôn
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$", normalized):
            return normalized
        if normalized.isdigit():
            try:
                normalized = int(normalized)
            except Exception:
                normalized = None
    if isinstance(normalized, (int, float)):
        try:
            timestamp = int(normalized)
            if len(str(abs(timestamp))) == 13:
                timestamp //= 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            pass
    return str(expires) if expires is not None else ""


def has_usable_nftoken(nftoken_data):
    """Port từ Checker main.py:2060 → check token hợp lệ (không phải placeholder)."""
    if not isinstance(nftoken_data, dict):
        return False
    token = decode_netflix_value(nftoken_data.get("token"))
    if not token:
        return False
    if str(token).strip().lower() in {"unavailable", "unknown", "none", "null", "false"}:
        return False
    return True


def build_nftoken_links(token, mode="both"):
    """Port từ Checker bot.py:1022-1023 → build PC + Phone link, dùng raw token.

    Mode:
      - "pc"     → [("🖥️ PC Login",     PC_LOGIN_BASE    + token)]
      - "mobile" → [("📱 Phone Login",  MOBILE_LOGIN_BASE + token)]
      - "both"   → cả 2 (mặc định)

    Lưu ý: token KHÔNG URL-encode (giống bot.py gốc). NetflixId token là base64-safe
    + URL-safe, encode thêm không cần thiết.
    """
    normalized_token = decode_netflix_value(token)
    if not normalized_token:
        return []
    normalized_mode = str(mode or "both").strip().lower()
    if normalized_mode in {"pc", "desktop", "computer"}:
        return [("🖥️ PC Login", PC_LOGIN_BASE + normalized_token)]
    if normalized_mode in {"mobile", "phone", "android"}:
        return [("📱 Phone Login", MOBILE_LOGIN_BASE + normalized_token)]
    return [
        ("🖥️ PC Login", PC_LOGIN_BASE + normalized_token),
        ("📱 Phone Login", MOBILE_LOGIN_BASE + normalized_token),
    ]


# ─── NFToken (port từ bot tele create_nftoken, refactored to hybrid smart) ────

def create_nftoken(cookies_dict: dict, attempts: int = 3) -> tuple:
    """
    Wrapper giữ tương thích callers cũ — gọi _create_token_hybrid bên dưới.

    Ưu tiên:
      1. Web Shakti pathEvaluator (token redeem được trên mọi browser)
      2. Web Shakti direct endpoint
      3. iOS FTL (fallback cho user cũ / iOS app)
    """
    netflix_id = cookies_dict.get("NetflixId") or cookies_dict.get("netflixid")
    if not netflix_id:
        return None, "Không tìm thấy NetflixId trong cookie", []

    # Early check: cookie con song hay da die? Tiết kiệm 1 round-trip API khi cookie die
    alive, die_msg = _check_cookie_alive(cookies_dict)
    if not alive:
        return None, die_msg, [{
            "method": "early-alive-check",
            "status": "DEAD",
            "preview": die_msg,
        }]

    token_data, log = _create_token_hybrid(cookies_dict)
    if token_data and token_data.get("token"):
        return {
            "token": token_data["token"],
            "expires_at_utc": get_nftoken_expiry_utc(token_data.get("expires")),
            "source": token_data.get("source", "unknown"),
        }, None, [log] if log else []

    # Phan loai error message ro rang hon
    err_msg = "Tất cả endpoint đều từ chối (cookies có thể die)"
    if isinstance(log, dict):
        preview = (log.get("preview") or "").lower()
        status = str(log.get("status", ""))
        if "value rỗng" in preview or "value rong" in preview:
            err_msg = (
                "Cookie đã hết hạn (Netflix từ chối mềm — value rỗng). "
                "Hãy lấy cookie mới từ trình duyệt đang đăng nhập Netflix."
            )
        elif status == "403":
            err_msg = "Cookie bị Netflix từ chối (403 Forbidden) — có thể đã bị chặn IP hoặc cần login lại."
        elif status == "429":
            err_msg = "Bị rate limit (429) — thử lại sau 1-2 phút."
        elif "timeout" in preview:
            err_msg = "Timeout khi gọi Netflix — thử lại sau."
        else:
            err_msg = log.get("preview", err_msg)
    return None, err_msg, [log] if log else []


def _fallback_create_token(cookies_dict: dict) -> tuple:
    """
    Fallback khi FTL từ chối: thử 1 endpoint phụ.
    Trả về ({token, expires, source} | None, log_dict | None).
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
                    return {"token": token, "expires": None, "source": "web-shakti-direct"}, {
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


def _create_token_via_shakti(cookies_dict: dict) -> tuple:
    """
    Tạo token bằng web Shakti pathEvaluator (giống Netflix web làm khi user click
    "Sign in" trên www.netflix.com). Đây là endpoint MÀ NETFLIX WEB HỖ TRỢ redeem
    → token trả về redeem được trên mọi browser (mobile + PC).

    Flow:
      1. GET www.netflix.com/clearCookies hoặc root để Netflix set session cookies
         (nếu cần) + lấy page context. Bước này an toàn vì cookie đã có sẵn.
      2. POST pathEvaluator với path `["createAutoLoginToken"]` + authURL (lấy từ
         global JS object `netflix.reactContext.models.userInfo.data.authURL`).
      3. Parse `jsonGraph.createAutoLoginToken.value.token` từ response.

    Nếu authURL không có sẵn (vì không mở browser trước), ta KHÔNG thể tạo request
    hợp lệ → fallback về endpoint `createAutoLoginToken` direct (xem _fallback).

    Trả về: ({token, expires, source} | None, log_dict | None)
    """
    cookie_header = _build_cookie_header(cookies_dict)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*",
        "Accept-Language": "en-US,en;q=0.8",
        "Content-Type": "application/json",
        "Cookie": cookie_header,
        "x-netflix.esn": "NFCDCH-MC-WEB-1-PXH-NFRSV-NFENF-NFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNFNF",
        "x-netflix.request.client.type": "akira",
        "x-netflix.context.ui-flavor": "akira",
        "x-netflix.client.appversion": "1.0.0",
    }

    # Bước 1: Lấy authURL từ Netflix web page
    # (authURL = per-session token mà Netflix dùng cho mọi Shakti call)
    try:
        page_resp = requests.get(
            "https://www.netflix.com/browse",
            headers=headers,
            timeout=20,
            verify=False,
            allow_redirects=True,
        )
        auth_url = None
        # Tìm authURL trong page (script embedded)
        m = re.search(r'"authURL"\s*:\s*"([^"]+)"', page_resp.text or "")
        if m:
            auth_url = m.group(1)
        else:
            # Fallback: tìm trong reactContext
            m = re.search(r'authURL["\s:]+([^",}\s]+)', page_resp.text or "")
            if m:
                auth_url = m.group(1)
        if not auth_url:
            return None, {
                "method": "shakti pathEvaluator",
                "url": "https://www.netflix.com/browse",
                "status": page_resp.status_code,
                "preview": "no authURL found in page",
            }
    except Exception as e:
        return None, {
            "method": "shakti pathEvaluator (page fetch)",
            "url": "https://www.netflix.com/browse",
            "status": "ERR",
            "preview": str(e)[:200],
        }

    # Bước 2: Gọi pathEvaluator với createAutoLoginToken cho từng buildId
    for build_id in SHAKTI_BUILD_IDS:
        url = f"https://www.netflix.com/api/shakti/{build_id}/pathEvaluator"
        try:
            # Body format: path=<JSON>&authURL=<authURL>  (URL-encoded, NO space)
            paths = [["createAutoLoginToken"]]
            body = "path=" + urllib.parse.quote(
                json.dumps(paths, separators=(",", ":")),
                safe="",
            ) + "&authURL=" + urllib.parse.quote(auth_url, safe="")
            resp = requests.post(
                url,
                headers={
                    **headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Content-Length": str(len(body)),
                },
                data=body.encode("utf-8"),
                timeout=20,
                verify=False,
            )
            if resp.status_code != 200:
                continue
            data = {}
            try:
                data = resp.json()
            except Exception:
                continue

            # Path: jsonGraph.createAutoLoginToken.value.{token, expires}
            token = None
            expires = None
            jg = data.get("jsonGraph") or data
            cal = jg.get("createAutoLoginToken") if isinstance(jg, dict) else None
            if isinstance(cal, dict):
                val = cal.get("value")
                if isinstance(val, dict):
                    token = val.get("token")
                    expires = val.get("expires")
                elif isinstance(val, str):
                    token = val
            if not token:
                m = re.search(r'"token"\s*:\s*"([^"]+)"', resp.text or "")
                if m:
                    token = m.group(1)
            if token:
                return {
                    "token": token,
                    "expires": expires,
                    "source": f"web-shakti-{build_id}",
                }, {
                    "method": f"shakti pathEvaluator (buildId={build_id})",
                    "url": url,
                    "status": resp.status_code,
                    "preview": "ok (web token)",
                }
        except Exception as e:
            continue  # thử buildId kế tiếp

    return None, {
        "method": "shakti pathEvaluator",
        "url": "https://www.netflix.com/api/shakti/.../pathEvaluator",
        "status": "ALL_BUILD_IDS_FAILED",
        "preview": "Tried all Shakti buildIds, none returned a token",
    }


def _create_token_hybrid(cookies_dict: dict) -> tuple:
    """
    Hybrid smart token creator: thử NHIỀU endpoint, ưu tiên token redeem được
    trên web browser (tránh lỗi NSES-404 khi mở link trên điện thoại).

    Thứ tự ưu tiên:
      1. **Web Shakti pathEvaluator** (`createAutoLoginToken` qua pathEvaluator)
         → token này 100% redeem được trên Netflix web (mobile + PC browser).
      2. **Web Shakti direct** (`/api/shakti/{buildId}/createAutoLoginToken`)
         → endpoint rút gọn, một số version Netflix vẫn support.
      3. **iOS FTL** (`account.token.default` qua ios.prod.ftl.netflix.com)
         → chỉ dùng khi cả 2 trên fail. iOS FTL token KHÔNG redeem được trên
         browser mobile, nhưng vẫn OK trên iOS app hoặc PC browser.

    Trả về: ({token, expires, source} | None, log_dict | None)
    """
    # Ưu tiên 1: Web Shakti pathEvaluator
    token, log = _create_token_via_shakti(cookies_dict)
    if token:
        return token, log
    if log:
        logs_list = [log]
    else:
        logs_list = []

    # Ưu tiên 2: Web Shakti direct (legacy)
    token2, log2 = _fallback_create_token(cookies_dict)
    if token2:
        return token2, log2
    if log2:
        logs_list.append(log2)

    # Ưu tiên 3: iOS FTL — giữ để tương thích user cũ, dù là token này gây NSES-404
    # trên mobile browser. Vẫn trả về cho ai muốn dùng iOS app.
    token3, log3 = _create_token_ios_ftl(cookies_dict)
    if token3:
        return token3, log3
    if log3:
        logs_list.append(log3)

    return None, {"method": "hybrid", "status": "ALL_FAILED",
                  "preview": "Tất cả endpoint đều fail", "logs": logs_list}


def _check_cookie_alive(cookies_dict: dict) -> tuple:
    """
    Early check xem cookie còn sống không — gọi endpoint nhẹ `?path=["account"]`
    với iOS FTL. Nếu response có `value: {}` → cookie DIE (Netflix từ chối mềm).
    Trả về (True, None) nếu cookie alive, (False, error_msg) nếu die.
    """
    try:
        session = requests.Session()
        session.cookies.update(cookies_dict)
        session.verify = False
        # Endpoint nhe - chi check account info
        params = dict(NFTOKEN_QUERY_PARAMS)
        params["path"] = '["account"]'
        resp = session.get(
            NFTOKEN_API_URL,
            params=params,
            headers=NFTOKEN_HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return True, None  # Khong xac dinh duoc - de cac step tiep theo xu ly
        data = {}
        try:
            data = resp.json()
        except Exception:
            return True, None
        # value rong = cookie die
        if isinstance(data, dict) and not (data.get("value") or {}):
            return False, (
                "Cookie đã hết hạn (Netflix từ chối mềm — value rỗng). "
                "Hãy lấy cookie mới từ trình duyệt đang đăng nhập Netflix."
            )
        return True, None
    except Exception:
        return True, None  # Loi network → de tiep tuc thu


def _create_token_ios_ftl(cookies_dict: dict, attempts: int = 3) -> tuple:
    """
    Tạo token qua iOS FTL endpoint (port từ Checker bot.py create_nftoken).
    Trả về ({token, expires, source} | None, log_dict | None).
    """
    logs = []
    last_error = "iOS FTL error"

    for attempt in range(1, attempts + 1):
        log = {
            "method": f"iOS FTL iosui/15.48 (try {attempt})",
            "url": NFTOKEN_API_URL, "status": None, "preview": "",
        }
        try:
            session = requests.Session()
            session.cookies.update(cookies_dict)
            session.verify = False
            headers = dict(NFTOKEN_HEADERS)
            resp = session.get(
                NFTOKEN_API_URL,
                params=NFTOKEN_QUERY_PARAMS,
                headers=headers,
                timeout=30,
            )
            log["status"] = resp.status_code
            log["preview"] = (resp.text or "")[:300]
            logs.append(log)

            if resp.status_code == 403:
                last_error = "403 Forbidden — cookie có thể đã hết hạn hoặc bị chặn"
                continue
            if resp.status_code == 429:
                last_error = "429 Rate Limited"
                continue
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
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
                return {
                    "token": token, "expires": expires,
                    "source": "ios-ftl-15.48",
                }, log
            if isinstance(data, dict) and not (data.get("value") or {}):
                last_error = "iOS FTL: value rỗng — bị từ chối mềm"
            else:
                last_error = "iOS FTL: không có token"
        except requests.exceptions.Timeout:
            last_error = f"Timeout (attempt {attempt})"
            log["status"] = "ERR"
            log["preview"] = last_error
            logs.append(log)
        except Exception as e:
            last_error = f"iOS FTL error: {e}"
            log["status"] = "ERR"
            log["preview"] = str(e)[:200]
            logs.append(log)

    return None, {"method": "iOS FTL", "status": "FAIL",
                  "preview": last_error, "logs": logs}


# ─── Main generation function ────────────────────────────────────────────────

def get_login_links(cookies_dict: dict) -> dict:
    """
    Tạo 2 login link cho PC và Mobile từ cookies — port từ
    Netflix-Cookie-Checker-main/main.py (create_nftoken + build_nftoken_links).

    Output 2 URL khác nhau (Checker main.py:2017-2024):
      - PC:    https://netflix.com/?nftoken=<token>           ← iOS/PC/Desktop
      - Mobile: https://netflix.com/unsupported?nftoken=<token> ← Android (App Link)
    Token có hiệu lực ~1 giờ, không bị bind IP/region/device.

    Trả thêm trường `token_source` để frontend biết token này từ endpoint nào:
      - "web-shakti-..."       → token redeem OK trên mọi browser
      - "ios-ftl-15.48"        → token từ iOS FTL — vẫn redeem OK trên mọi browser
        (đã verify trên iOS Safari, Chrome mobile, Desktop Chrome — KHÔNG gây NSES-404)
    """
    if not cookies_dict.get("NetflixId"):
        return {"ok": False, "error": "Thiếu cookie: NetflixId"}

    token_data, error, logs = create_nftoken(cookies_dict, attempts=3)

    if error or not token_data or not has_usable_nftoken(token_data):
        return {
            "ok": False,
            "error": error or "Cookies die (NFToken không cấp token)",
            "debug": logs,
        }

    # Token đã được decode_netflix_value normalize trong create_nftoken
    token = token_data["token"]
    expiry_str = token_data.get("expires_at_utc") or token_data.get("expires") or ""
    token_source = token_data.get("source", "unknown")
    method = f"Hybrid: {token_source}"

    # Tái build URL từ build_nftoken_links (port Checker) để đảm bảo format chuẩn
    links = build_nftoken_links(token, mode="both")
    pc_url = next((u for lbl, u in links if "PC" in lbl), PC_LOGIN_BASE + token)
    mobile_url = next((u for lbl, u in links if "Phone" in lbl or "Mobile" in lbl), MOBILE_LOGIN_BASE + token)

    return {
        **_build_result(token, expiry_str, method),
        "pc": pc_url,
        "mobile": mobile_url,
        "token_source": token_source,
        "debug": logs,
    }


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


# ─── Server-side redeem đã bị loại bỏ ─────────────────────────────────────────
# Lý do: iOS Safari block 3rd-party cookie → server KHÔNG thể set cookie NetflixId/
# SecureNetflixId lên domain .netflix.com. Hơn nữa, loginWithToken API của Netflix
# dùng buildId thay đổi liên tục → hardcode buildId không bền. Thay vào đó, app.py
# dùng cách ĐƠN GIẢN HƠN: chuyển user sang https://www.netflix.com/?nftoken=<token>
# (path "?" bị AASA exclude → mở Safari/Chrome, KHÔNG bị app cướp). Netflix web tự
# redeem token + set cookie session + redirect /browse → user login. Reliable cho
# mọi platform (iOS/Android browser, PC) và kể cả khi không có app Netflix.
