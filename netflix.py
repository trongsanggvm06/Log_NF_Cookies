"""
Netflix Login Link Generator

Sử dụng Netflix iOS FTL (Falcor) endpoint — giả lập là iOS app Argo 15.48.
Path: ["account","token","default"] → trả về { token, expires }.

Chỉ cần cookie NetflixId. Token base64 dùng làm nftoken trong URL.

Ref discovery: github.com/harshitkamboj/Netflix-NFToken-Generator
"""
import json
import re
import random
import string
import uuid
import urllib.parse
from datetime import datetime, timezone

import requests
from urllib3.exceptions import InsecureRequestWarning

from config import USER_AGENT, PC_LOGIN_BASE, MOBILE_LOGIN_BASE, CUSTOM_ENDPOINT

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def _gen_esn() -> str:
    """Sinh ESN random theo format: NFAPPL-02-IPHONE8=1-PXA-<128 ký tự base32>."""
    chars = string.digits + string.ascii_uppercase
    suffix = "".join(random.choice(chars) for _ in range(128))
    return f"NFAPPL-02-IPHONE8=1-PXA-{suffix}"


def _gen_uuid() -> str:
    return str(uuid.uuid4()).upper()


# ─── Constants — iOS FTL endpoint ─────────────────────────────────────────────

FTL_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"

CONFIG_BLOB = (
    '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false",'
    '"cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true",'
    '"addHorizontalBoxArtToVideoSummariesEnabled":"false",'
    '"skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false",'
    '"baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true",'
    '"postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false",'
    '"roarEnabled":"false","useSeason1AltLabelEnabled":"false",'
    '"disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],'
    '"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true",'
    '"kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true",'
    '"contentWarningEnabled":"true","videosInPopularGamesEnabled":"true",'
    '"avifFormatEnabled":"false","sharksEnabled":"true"}'
)


def _build_query_params(esn: str) -> dict:
    return {
        "appVersion": "15.48.1",
        "config": CONFIG_BLOB,
        "device_type": "NFAPPL-02-",
        "esn": esn,  # raw — requests sẽ URL-encode đúng cách
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


def _build_headers(esn: str, profile_guid: str, top_uuid: str, user_action_uuid: str) -> dict:
    return {
        "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
        "x-netflix.request.attempt": "1",
        "x-netflix.request.client.user.guid": profile_guid,
        "x-netflix.context.profile-guid": profile_guid,
        "x-netflix.request.routing": (
            '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}'
        ),
        "x-netflix.context.app-version": "15.48.1",
        "x-netflix.argo.translated": "true",
        "x-netflix.context.form-factor": "phone",
        "x-netflix.context.sdk-version": "2012.4",
        "x-netflix.client.appversion": "15.48.1",
        "x-netflix.context.max-device-width": "375",
        "x-netflix.context.ab-tests": "",
        "x-netflix.tracing.cl.useractionid": user_action_uuid,
        "x-netflix.client.type": "argo",
        "x-netflix.client.ftl.esn": esn,
        "x-netflix.context.locales": "en-US",
        "x-netflix.context.top-level-uuid": top_uuid,
        "x-netflix.client.iosversion": "15.8.5",
        "accept-language": "en-US;q=1",
        "x-netflix.argo.abtests": "",
        "x-netflix.context.os-version": "15.8.5",
        "x-netflix.request.client.context": '{"appState":"foreground"}',
        "x-netflix.context.ui-flavor": "argo",
        "x-netflix.argo.nfnsm": "9",
        "x-netflix.context.pixel-density": "2.0",
        "x-netflix.request.toplevel.uuid": top_uuid,
        "x-netflix.request.client.timezoneid": "Asia/Ho_Chi_Minh",
    }


COOKIE_KEYS = ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn")


# ─── Cookie parser ────────────────────────────────────────────────────────────

def _decode_cookie_value(value: str) -> str:
    if isinstance(value, str) and "%" in value:
        try:
            return urllib.parse.unquote(value)
        except Exception:
            return value
    return value


def split_cookie_blocks(raw: str) -> list:
    """
    Tách input thành nhiều block cookie. Tự động detect 3 kiểu phân cách:
    1. Dùng "----" giữa các block (legacy)
    2. Nhiều JSON array dính nhau: [{...}][{...}] hoặc cách nhau bằng whitespace
    3. Cách nhau bằng dòng trắng (2+ newline liên tiếp)
    Nếu không match kiểu nào → trả về 1 block duy nhất.
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

    # 3. Raw cookie string: nhiều "NetflixId=" trong text → mỗi cái là 1 block
    #    Format ví dụ: "NetflixId=xxx; SecureNetflixId=yyy;\nNetflixId=aaa; ..."
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

    # 4. Split theo dòng trắng (2+ newline)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs

    # 5. Fallback: 1 block duy nhất
    return [text]


def parse_cookies(raw: str) -> dict:
    """
    Hỗ trợ 3 định dạng:
    - JSON array (export từ Cookie-Editor / EditThisCookie)
    - JSON object {"NetflixId": "...", ...}
    - Chuỗi thuần "NetflixId=...; SecureNetflixId=..."
    """
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

    # Fallback: regex tìm trong chuỗi thô
    for key in COOKIE_KEYS:
        if key in cookie_dict:
            continue
        match = re.search(rf"(?<!\w){re.escape(key)}=([^;,\s]+)", text)
        if match:
            cookie_dict[key] = _decode_cookie_value(match.group(1))

    return cookie_dict


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


def _make_result(token: str, expiry) -> dict:
    return {
        "ok": True,
        "pc": PC_LOGIN_BASE + token,
        "mobile": MOBILE_LOGIN_BASE + token,
        "expiry": _fmt_expiry(expiry),
        "build_id": "iosui/15.48",
    }


def _extract_profile_guid(netflix_id: str) -> str:
    """NetflixId chứa pg=GUID — lấy ra để dùng làm profile-guid trong headers."""
    m = re.search(r"pg=([A-Z0-9]+)", netflix_id)
    if m:
        return m.group(1)
    return "A4CS633D7VCBPE2GPK2HL4EKOE"  # fallback


def _build_cookie_header(cookies_dict: dict) -> str:
    parts = []
    for k in ("NetflixId", "SecureNetflixId", "nfvdid", "flwssn", "OptanonConsent"):
        v = cookies_dict.get(k)
        if v:
            parts.append(f"{k}={v}")
    return "; ".join(parts)


def _try_request(target_url: str, cookies_dict: dict, attempt_label: str) -> dict:
    """1 lần thử với ESN + UUIDs random. Trả về dict gồm log + token (nếu có)."""
    netflix_id = cookies_dict["NetflixId"]
    esn = _gen_esn()
    profile_guid = _extract_profile_guid(netflix_id)
    top_uuid = _gen_uuid()
    user_action_uuid = _gen_uuid()

    headers = _build_headers(esn, profile_guid, top_uuid, user_action_uuid)
    headers["Cookie"] = _build_cookie_header(cookies_dict)
    params = _build_query_params(esn)

    try:
        resp = requests.get(target_url, params=params, headers=headers,
                            timeout=20, verify=False)
    except requests.RequestException as e:
        return {
            "log": {"url": f"{attempt_label}: {target_url}",
                    "status": "ERR", "preview": str(e)[:300]},
            "token": None, "expires": None,
        }

    log = {
        "url": f"{attempt_label}: {target_url}",
        "status": resp.status_code,
        "len": len(resp.text or ""),
        "preview": (resp.text or "")[:800],
    }

    if resp.status_code != 200:
        return {"log": log, "token": None, "expires": None}

    try:
        data = resp.json()
    except Exception:
        return {"log": log, "token": None, "expires": None}

    token_data = (
        (((data.get("value") or {}).get("account") or {}).get("token") or {}).get("default")
        or {}
    )
    return {
        "log": log,
        "token": token_data.get("token"),
        "expires": token_data.get("expires"),
    }


# ─── Hàm chính ────────────────────────────────────────────────────────────────

def get_login_links(cookies_dict: dict) -> dict:
    if not cookies_dict.get("NetflixId"):
        return {"ok": False, "error": "Thiếu cookie: NetflixId"}

    debug: list = []
    target_url = CUSTOM_ENDPOINT or FTL_URL

    # Thử lần 1 với fresh ESN + all cookies
    r = _try_request(target_url, cookies_dict, "try1")
    debug.append(r["log"])
    if r["token"]:
        return {**_make_result(r["token"], r["expires"]), "debug": debug}

    # Retry với fresh ESN+UUID khác (đôi khi Netflix throttle 1 request đầu)
    r = _try_request(target_url, cookies_dict, "try2")
    debug.append(r["log"])
    if r["token"]:
        return {**_make_result(r["token"], r["expires"]), "debug": debug}

    # Retry lần 3
    r = _try_request(target_url, cookies_dict, "try3")
    debug.append(r["log"])
    if r["token"]:
        return {**_make_result(r["token"], r["expires"]), "debug": debug}

    last = debug[-1]
    return {
        "ok": False,
        "error": f"HTTP {last.get('status')} sau 3 lần thử (ESN khác nhau) — cookie có thể đã hết hạn hoặc IP bị Netflix flag",
        "debug": debug,
    }


# ─── Debug probe (giữ tương thích cũ) ─────────────────────────────────────────

def probe_endpoint(cookies_dict: dict, url: str, method: str = "POST") -> dict:
    """Thử 1 endpoint tuỳ ý — dùng cho tab Debug."""
    netflix_id = cookies_dict.get("NetflixId", "")
    profile_guid = _extract_profile_guid(netflix_id) if netflix_id else "PROFILE"
    headers = _build_headers(_gen_esn(), profile_guid, _gen_uuid(), _gen_uuid())
    if cookies_dict:
        headers["Cookie"] = _build_cookie_header(cookies_dict)

    try:
        if method.upper() == "POST":
            resp = requests.post(url, headers=headers, timeout=15, verify=False)
        else:
            resp = requests.get(url, headers=headers, timeout=15, verify=False)
        body_preview = (resp.text or "")[:1500]
        return {
            "status": resp.status_code,
            "body": body_preview,
            "build_id": "iosui/15.48",
            "auth_url_present": False,
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": "token" in body_preview.lower(),
        }
    except Exception as e:
        return {
            "status": "ERR",
            "body": str(e)[:300],
            "build_id": "iosui/15.48",
            "auth_url_present": False,
            "cookies_sent": list(cookies_dict.keys()),
            "token_found": False,
        }
