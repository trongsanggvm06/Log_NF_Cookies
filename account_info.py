"""
account_info.py — Trích xuất thông tin tài khoản Netflix (port từ bot tele /checkacc).

Logic giống hệt Netflix-Cookie-Checker-main/bot.py:
  - get_account_info(): tải trang account/membership bằng cookie
  - extract_info(): bóc tách plan, giá, billing, payment, profiles, country…
  - build_account_summary(): gom thành dict gọn cho web JSON
  - format_account_reply(): chuỗi text giống hệt bot (dùng khi cần)
"""
import html
import re
import unicodedata
import urllib.parse
from datetime import datetime

import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Account page headers (giống bot)
ACCOUNT_PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Encoding": "identity",
}


# ─── Decode helpers ───────────────────────────────────────────────────────────

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
    if value is None:
        return None
    cleaned = html.unescape(str(value))
    replacements = {
        "\\x20": " ", "\\u00A0": " ", "\\u00a0": " ", "&nbsp;": " ", "u00A0": " ",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    cleaned = cleaned.replace("\\/", "/").replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
    for _ in range(3):
        previous = cleaned
        cleaned = re.sub(r"\\u([0-9a-fA-F]{4})", _decode_unicode_escape, cleaned)
        cleaned = re.sub(r"\\x([0-9a-fA-F]{2})", _decode_hex_escape, cleaned)
        cleaned = re.sub(r"(?<!\\)\bu([0-9a-fA-F]{4})(?![0-9a-fA-F])", _decode_unicode_escape, cleaned)
        cleaned = cleaned.replace("\\\\", "\\")
        if cleaned == previous:
            break
    cleaned = re.sub(r"(?<=[A-Za-z])\s+(?=[^\x00-\x7F])", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def extract_first_match(response_text, patterns, flags=0):
    for pattern in patterns:
        match = re.search(pattern, response_text, flags)
        if match:
            return decode_netflix_value(match.group(1))
    return None


def parse_boolean_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, dict):
        for key in ("value", "isUserOnHold", "holdStatus", "isOnHold", "pastDue", "isPastDue", "isVerified", "verified"):
            if key in value:
                parsed = parse_boolean_value(value.get(key))
                if parsed is not None:
                    return parsed
        return None
    cleaned = decode_netflix_value(value)
    if cleaned is None:
        return None
    lowered = str(cleaned).strip().lower()
    if lowered in {"true", "yes", "1", "on"}:
        return True
    if lowered in {"false", "no", "0", "off"}:
        return False
    return None


def format_boolean_label(value):
    parsed = parse_boolean_value(value)
    if parsed is True:
        return "Yes"
    if parsed is False:
        return "No"
    return None


def extract_bool_value(response_text, patterns):
    value = extract_first_match(response_text, patterns, re.IGNORECASE)
    if value is None:
        return None
    parsed = format_boolean_label(value)
    if parsed is not None:
        return parsed
    return value


def normalize_plan_key(plan_name):
    if not plan_name:
        return "unknown"
    simplified = unicodedata.normalize("NFKD", plan_name)
    simplified = "".join(ch for ch in simplified if not unicodedata.combining(ch))
    normalized = re.sub(r"[^\w]+", "_", simplified.lower(), flags=re.UNICODE).strip("_")
    return normalized or "unknown"


def _int_or_none(value):
    cleaned = decode_netflix_value(value)
    if cleaned is None:
        return None
    try:
        return int(str(cleaned).strip())
    except Exception:
        match = re.search(r"\d+", str(cleaned))
        if match:
            try:
                return int(match.group(0))
            except Exception:
                return None
        return None


def normalize_phone_number(value, country_code=None):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return None
    if str(cleaned).startswith("+"):
        return cleaned
    digits = re.sub(r"\D+", "", str(cleaned))
    if not digits:
        return cleaned
    normalized_country = (decode_netflix_value(country_code) or "").strip().upper()
    dial_prefix_map = {"IN": "91"}
    dial_prefix = dial_prefix_map.get(normalized_country)
    if dial_prefix and digits.startswith("0") and len(digits) >= 10:
        return f"+{dial_prefix}{digits.lstrip('0')}"
    return cleaned


def country_code_to_flag(country_code):
    raw = (decode_netflix_value(country_code) or "").strip()
    if not raw:
        return ""
    upper = raw.upper()
    if len(upper) == 2 and upper.isalpha():
        return "".join(chr(127397 + ord(char)) for char in upper)
    return ""


MONTH_ALIASES = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "juin": 6, "juillet": 7,
    "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}


def normalize_calendar_year(year):
    try:
        year = int(year)
    except Exception:
        return None
    if 2400 <= year <= 2700:
        return year - 543
    return year


def parse_localized_date(cleaned):
    if not cleaned:
        return None
    for parser in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(cleaned, parser)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except Exception:
        pass
    numeric_parts = [int(part) for part in re.findall(r"\d+", cleaned)]
    if len(numeric_parts) >= 3:
        a, b, c = numeric_parts[0], numeric_parts[1], numeric_parts[2]
        try:
            a = normalize_calendar_year(a)
            c = normalize_calendar_year(c)
            if a and 1900 <= a <= 3000 and 1 <= b <= 12 and 1 <= c <= 31:
                return datetime(a, b, c)
            if c and 1 <= a <= 31 and 1 <= b <= 12 and 1900 <= c <= 3000:
                return datetime(c, b, a)
        except Exception:
            pass
    raw_lower = cleaned.lower()
    month = None
    for alias, alias_month in MONTH_ALIASES.items():
        if alias in raw_lower:
            month = alias_month
            break
    if month is None:
        return None
    year = None
    for number in numeric_parts:
        normalized_year = normalize_calendar_year(number)
        if normalized_year is not None and 1900 <= normalized_year <= 3000:
            year = normalized_year
            break
    if year is None:
        return None
    day = 1
    for number in numeric_parts:
        if normalize_calendar_year(number) == year:
            continue
        if 1 <= number <= 31:
            day = number
            break
    try:
        return datetime(year, month, day)
    except Exception:
        return None


def format_display_date(value):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return None
    parsed = parse_localized_date(cleaned)
    if parsed is not None:
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    return cleaned


def format_member_since(value):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return None
    parsed = parse_localized_date(cleaned)
    if parsed is not None:
        return parsed.strftime("%B %Y")
    numeric_parts = re.findall(r"\d+", cleaned)
    if len(numeric_parts) >= 2:
        try:
            month = int(numeric_parts[0])
            year = normalize_calendar_year(numeric_parts[-1])
            if year and 1 <= month <= 12 and 1900 <= year <= 3000:
                return datetime(year, month, 1).strftime("%B %Y")
        except Exception:
            pass
    return cleaned


# ─── GraphQL payload extraction ─────────────────────────────────────────────────

def extract_info_from_graphql_payload(response_text):
    try:
        import json
        payload = json.loads(response_text)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}

    growth_account = data.get("growthAccount") or {}
    current_profile = data.get("currentProfile") or {}
    current_plan = ((growth_account.get("currentPlan") or {}).get("plan") or {})
    next_plan = ((growth_account.get("nextPlan") or {}).get("plan") or {})
    next_billing = growth_account.get("nextBillingDate") or {}
    hold_meta = growth_account.get("growthHoldMetadata") or {}
    local_phone = growth_account.get("growthLocalizablePhoneNumber") or {}
    raw_phone = local_phone.get("rawPhoneNumber") or {}
    payment_methods = growth_account.get("growthPaymentMethods") or []
    payment_method = payment_methods[0] if payment_methods and isinstance(payment_methods[0], dict) else {}
    payment_logo = (payment_method.get("paymentOptionLogo") or {}).get("paymentOptionLogo")
    payment_typename = str(payment_method.get("__typename") or "")
    payment_display_text = decode_netflix_value(payment_method.get("displayText"))
    profiles = growth_account.get("profiles") or []

    phone_digits = None
    phone_country_code = None
    if isinstance(raw_phone, dict):
        phone_digits_obj = raw_phone.get("phoneNumberDigits") or {}
        phone_digits = phone_digits_obj.get("value") if isinstance(phone_digits_obj, dict) else raw_phone.get("phoneNumberDigits")
        phone_country_code = raw_phone.get("countryCode")
    else:
        phone_digits = raw_phone

    def _growth_email(profile_obj):
        if not isinstance(profile_obj, dict):
            return None, None
        growth_email = profile_obj.get("growthEmail") or {}
        email_obj = growth_email.get("email") or {}
        email_value = email_obj.get("value") if isinstance(email_obj, dict) else None
        return email_value, growth_email.get("isVerified")

    email_value, email_verified = _growth_email(current_profile)
    if not email_value:
        for profile in profiles:
            email_value, email_verified = _growth_email(profile)
            if email_value:
                break

    profile_names = []
    for profile in profiles:
        if isinstance(profile, dict):
            name = decode_netflix_value(profile.get("name"))
            if name and name not in profile_names:
                profile_names.append(name)

    feature_types = []
    for plan_obj in (current_plan, next_plan):
        for feature in (plan_obj.get("availableFeatures") or []):
            if isinstance(feature, dict) and feature.get("type"):
                feature_types.append(str(feature["type"]).upper())

    def _first_boolean_label(*candidates):
        for candidate in candidates:
            labeled = format_boolean_label(candidate)
            if labeled is not None:
                return labeled
        return None

    def _extract_price_value(plan_obj):
        if not isinstance(plan_obj, dict):
            return None
        for key in ("priceDisplay", "displayPrice", "formattedPrice", "formattedPlanPrice", "planPriceDisplay"):
            decoded = decode_netflix_value(plan_obj.get(key))
            if decoded:
                return decoded
        price_obj = plan_obj.get("price")
        if isinstance(price_obj, dict):
            for key in ("displayValue", "formatted", "formattedPrice", "displayPrice", "value", "amountDisplay"):
                decoded = decode_netflix_value(price_obj.get(key))
                if decoded:
                    return decoded
        return None

    hold_status = _first_boolean_label(
        hold_meta.get("isUserOnHold") if isinstance(hold_meta, dict) else hold_meta,
        hold_meta.get("holdStatus") if isinstance(hold_meta, dict) else None,
        growth_account.get("isUserOnHold"),
        growth_account.get("holdStatus"),
        growth_account.get("isOnHold"),
        growth_account.get("pastDue"),
    )

    info = {
        "accountOwnerName": decode_netflix_value(current_profile.get("name")),
        "email": decode_netflix_value(email_value),
        "countryOfSignup": decode_netflix_value(((growth_account.get("countryOfSignUp") or {}).get("code"))),
        "memberSince": decode_netflix_value(growth_account.get("memberSince")),
        "nextBillingDate": decode_netflix_value(next_billing.get("localDate") or next_billing.get("date")),
        "userGuid": decode_netflix_value(growth_account.get("ownerGuid") or current_profile.get("guid")),
        "showExtraMemberSection": "Yes" if "EXTRA_MEMBER" in feature_types else "No" if feature_types else None,
        "membershipStatus": decode_netflix_value(growth_account.get("membershipStatus")),
        "localizedPlanName": decode_netflix_value(current_plan.get("name") or next_plan.get("name")),
        "planPrice": _extract_price_value(current_plan) or _extract_price_value(next_plan),
        "paymentMethodType": decode_netflix_value(payment_logo or growth_account.get("payer")),
        "maskedCard": None,
        "phoneNumber": normalize_phone_number(phone_digits, phone_country_code),
        "videoQuality": decode_netflix_value(current_plan.get("videoQuality")),
        "holdStatus": hold_status,
        "emailVerified": format_boolean_label(email_verified),
        "profiles": profile_names if profile_names else None,
    }

    if "Card" in payment_typename:
        info["paymentMethodType"] = "CC"
        if payment_display_text:
            info["maskedCard"] = payment_display_text
    elif payment_display_text and payment_logo is None and not re.fullmatch(r"\d{4}", payment_display_text):
        info["paymentMethodType"] = info["paymentMethodType"] or payment_display_text

    return {k: v for k, v in info.items() if v not in (None, "", [], {})}


def extract_info(response_text):
    graphql_info = extract_info_from_graphql_payload(response_text)
    extracted = {
        "accountOwnerName": extract_first_match(response_text, [
            r'userInfo"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"',
            r'"accountOwnerName"\s*:\s*"([^"]+)"',
            r'"firstName"\s*:\s*"([^"]+)"',
        ]),
        "email": extract_first_match(response_text, [
            r'"emailAddress"\s*:\s*"([^"]+)"',
            r'"email"\s*:\s*"([^"]+)"',
            r'"loginId"\s*:\s*"([^"]+)"',
        ]),
        "countryOfSignup": extract_first_match(response_text, [
            r'"currentCountry"\s*:\s*"([^"]+)"',
            r'"countryOfSignup":\s*"([^"]+)"',
        ]),
        "memberSince": extract_first_match(response_text, [r'"memberSince":\s*"([^"]+)"']),
        "nextBillingDate": extract_first_match(response_text, [
            r'"GrowthNextBillingDate"\s*,\s*"date"\s*:\s*"([^"T]+)T',
            r'"nextBillingDate"\s*:\s*"([^"]+)"',
        ]),
        "userGuid": extract_first_match(response_text, [r'"userGuid":\s*"([^"]+)"']),
        "showExtraMemberSection": extract_bool_value(response_text, [
            r'"showExtraMemberSection":\s*\{\s*"fieldType":\s*"Boolean",\s*"value":\s*(true|false)',
            r'"showExtraMemberSection"\s*:\s*(true|false)',
        ]),
        "membershipStatus": extract_first_match(response_text, [r'"membershipStatus":\s*"([^"]+)"']),
        "maxStreams": extract_first_match(response_text, [
            r'maxStreams\":{\\"fieldType\\":\\"Numeric\\",\\"value\\":([^,]+),',
            r'"maxStreams"\s*:\s*"?([^",}]+)"?',
        ]),
        "localizedPlanName": extract_first_match(response_text, [
            r'"MemberPlan"\s*,\s*"fields"\s*:\s*\{\s*"localizedPlanName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'localizedPlanName\":{\\"fieldType\\":\\"String\\",\\"value\\":\\"([^"]+)"',
            r'"localizedPlanName"\s*:\s*"([^"]+)"',
            r'"planName"\s*:\s*"([^"]+)"',
        ]),
        "planPrice": extract_first_match(response_text, [
            r'"formattedPlanPrice"\s*:\s*"([^"]+)"',
            r'"formattedPrice"\s*:\s*"([^"]+)"',
            r'"displayPrice"\s*:\s*"([^"]+)"',
            r'"planPrice"\s*:\s*"([^"]+)"',
        ]),
        "paymentMethodType": extract_first_match(response_text, [
            r'"paymentMethod"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'"paymentMethod"\s*:\s*"([^"]+)"',
            r'"paymentMethodType"\s*:\s*"([^"]+)"',
        ]),
        "maskedCard": extract_first_match(response_text, [
            r'"__typename"\s*:\s*"GrowthCardPaymentMethod"[\s\S]*?"displayText"\s*:\s*"([^"]+)"',
            r'"paymentCardDisplayString"\s*:\s*"([^"]+)"',
            r'"lastFour"\s*:\s*"([^"]+)"',
        ]),
        "phoneNumber": extract_first_match(response_text, [
            r'"phoneNumberDigits"\s*:\s*\{[\s\S]*?"value"\s*:\s*"([^"]+)"',
            r'"phoneNumber"\s*:\s*"([^"]+)"',
        ]),
        "videoQuality": extract_first_match(response_text, [
            r'videoQuality"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            r'"videoQuality"\s*:\s*"([^"]+)"',
            r'"quality"\s*:\s*"([^"]+)"',
        ]),
        "holdStatus": extract_bool_value(response_text, [
            r'"holdStatus"\s*:\s*(true|false)',
            r'"isUserOnHold"\s*:\s*(true|false)',
            r'"pastDue"\s*:\s*(true|false)',
        ]),
        "emailVerified": extract_bool_value(response_text, [
            r'"emailVerified"\s*:\s*(true|false)',
            r'"isEmailVerified"\s*:\s*(true|false)',
        ]),
    }

    # Profile names
    profile_list = []
    for pattern in [
        r'"profileName"\s*:\s*"([^"]+)"',
        r'"profileName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
    ]:
        for found in re.findall(pattern, response_text, re.DOTALL):
            decoded = decode_netflix_value(found)
            if decoded and decoded not in profile_list:
                profile_list.append(decoded)
    for m in re.finditer(r'"__typename"\s*:\s*"Profile"', response_text):
        snippet = response_text[m.start():m.start() + 1200]
        nm = re.search(r'"name"\s*:\s*"([^"]+)"', snippet)
        if nm:
            decoded = decode_netflix_value(nm.group(1))
            if decoded and decoded not in profile_list:
                profile_list.append(decoded)
    extracted["profiles"] = profile_list if profile_list else None

    # Merge graphql on top
    for key, value in graphql_info.items():
        if value not in (None, "", [], {}):
            extracted[key] = value

    # Derive phone display
    phone_number = extracted.get("phoneNumber")
    extracted["phoneDisplay"] = normalize_phone_number(phone_number, extracted.get("countryOfSignup"))

    return extracted


def derive_plan_label(info, is_subscribed):
    raw_plan = decode_netflix_value(info.get("localizedPlanName"))
    raw_quality = decode_netflix_value(info.get("videoQuality"))
    streams = _int_or_none(info.get("maxStreams"))

    if not is_subscribed and not raw_plan:
        return "Free"

    normalized = normalize_plan_key(raw_plan) if raw_plan else ""

    plan_aliases = {
        "Premium": {"premium", "premium_extra_member", "cao_cap", "cao_c_ap", "ozel", "프리미엄", "プレミアム"},
        "Standard With Ads": {"standard_with_ads", "standardwithads", "estandar_con_anuncios", "광고형_스탠다드"},
        "Standard": {"standard", "estandar", "標準方案", "标准", "standaard", "스탠다드"},
        "Basic": {"basic", "basico", "dasar", "basique", "basis", "베이직", "ベーシック"},
        "Mobile": {"mobile", "ponsel", "seluler", "movil", "모바일", "モバイル"},
    }
    for label, aliases in plan_aliases.items():
        if normalized in aliases:
            return label

    if streams is not None:
        quality_norm = normalize_plan_key(raw_quality) if raw_quality else ""
        if streams >= 4 or quality_norm in {"uhd", "ultra_hd", "4k"}:
            return "Premium"
        if streams >= 2 or quality_norm in {"hd", "full_hd"}:
            return "Standard"
        if streams == 1:
            return "Mobile" if normalized in {"ponsel", "mobile"} else "Basic"

    if raw_plan:
        return raw_plan
    return "Free" if not is_subscribed else "Unknown"


def is_subscribed_account(info):
    status = normalize_plan_key((info or {}).get("membershipStatus") or "")
    if status == "current_member":
        return True
    localized = decode_netflix_value((info or {}).get("localizedPlanName")) or ""
    for marker in ("extra member", "miembro extra", "membro extra", "assinante extra"):
        if marker in localized.lower():
            return True
    return False


def is_extra_member_account(info):
    localized = decode_netflix_value((info or {}).get("localizedPlanName")) or ""
    for marker in ("extra member", "miembro extra", "membro extra", "assinante extra", "abbonato extra", "额外成员", "추가 회원"):
        if marker in localized.lower():
            return True
    return False


# ─── Fetch account page ─────────────────────────────────────────────────────────

def _cookie_header(cookies: dict) -> str:
    """Build Cookie header ở dạng URL-encoded giống trình duyệt gửi (khớp bot)."""
    parts = []
    for name, value in cookies.items():
        if not value:
            continue
        value = str(value)
        if "%" not in value:  # value đã decode → encode lại về dạng browser gửi
            value = urllib.parse.quote(value, safe="-_.~")
        parts.append(f"{name}={value}")
    return "; ".join(parts)


def get_account_info(cookies: dict) -> tuple:
    """Tải trang membership của Netflix và bóc tách thông tin (giống bot /checkacc)."""
    headers = dict(ACCOUNT_PAGE_HEADERS)
    headers["Cookie"] = _cookie_header(cookies)

    try:
        response = requests.get(
            "https://www.netflix.com/account/membership",
            headers=headers,
            timeout=30,
            verify=False,
        )
        if response.status_code == 200 and response.text:
            info = extract_info(response.text)
            return info, None
        elif response.status_code == 403:
            return None, "403 Forbidden — Cookie đã hết hạn hoặc không hợp lệ"
        elif response.status_code == 429:
            return None, "429 Rate Limited — Thử lại sau"
        else:
            return None, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return None, "Request timeout"
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


# ─── Output builders ─────────────────────────────────────────────────────────────

def build_account_summary(info: dict) -> dict:
    """Gom info thô thành dict gọn, sẵn sàng cho web JSON (đã derive plan, status…)."""
    is_subscribed = is_subscribed_account(info)
    is_extra = is_extra_member_account(info)
    plan_label = derive_plan_label(info, is_subscribed)

    country = decode_netflix_value(info.get("countryOfSignup")) or "UNKNOWN"
    streams = decode_netflix_value(str(info.get("maxStreams") or "").rstrip("}")) or None

    profiles = info.get("profiles") or []
    if isinstance(profiles, str):
        profiles = [p.strip() for p in profiles.split(",") if p.strip()]

    return {
        "status": "HIT" if is_subscribed else "FREE",
        "isSubscribed": is_subscribed,
        "isExtraMember": is_extra,
        "plan": plan_label,
        "name": decode_netflix_value(info.get("accountOwnerName")),
        "email": decode_netflix_value(info.get("email")),
        "country": country,
        "countryFlag": country_code_to_flag(country),
        "memberSince": format_member_since(info.get("memberSince")),
        "nextBilling": format_display_date(info.get("nextBillingDate")),
        "payment": decode_netflix_value(info.get("paymentMethodType")),
        "maskedCard": decode_netflix_value(info.get("maskedCard")),
        "phone": decode_netflix_value(info.get("phoneDisplay") or info.get("phoneNumber")),
        "quality": decode_netflix_value(info.get("videoQuality")),
        "maxStreams": streams,
        "price": decode_netflix_value(info.get("planPrice")),
        "holdStatus": decode_netflix_value(info.get("holdStatus")),
        "extraMember": "Yes" if is_extra else (decode_netflix_value(info.get("showExtraMemberSection")) or "No"),
        "emailVerified": decode_netflix_value(info.get("emailVerified")),
        "membershipStatus": decode_netflix_value(info.get("membershipStatus")),
        "profiles": profiles,
    }


def format_account_reply(info: dict) -> str:
    """Chuỗi text giống hệt bot /checkacc (giữ để tương thích / debug)."""
    is_subscribed = is_subscribed_account(info)
    is_extra = is_extra_member_account(info)
    plan_label = derive_plan_label(info, is_subscribed)

    status_emoji = "✅" if is_subscribed else "🆓"
    status_text = "HIT" if is_subscribed else "FREE"

    country = decode_netflix_value(info.get("countryOfSignup")) or "UNKNOWN"
    flag = country_code_to_flag(country)
    country_display = f"{country} {flag}".strip()

    name = decode_netflix_value(info.get("accountOwnerName")) or "UNKNOWN"
    email = decode_netflix_value(info.get("email")) or "UNKNOWN"
    member_since = format_member_since(info.get("memberSince")) or "UNKNOWN"
    next_billing = format_display_date(info.get("nextBillingDate")) or "UNKNOWN"
    payment = decode_netflix_value(info.get("paymentMethodType")) or "UNKNOWN"
    phone = decode_netflix_value(info.get("phoneDisplay") or info.get("phoneNumber")) or "UNKNOWN"
    quality = decode_netflix_value(info.get("videoQuality")) or "UNKNOWN"
    streams = decode_netflix_value(str(info.get("maxStreams") or "").rstrip("}")) or "UNKNOWN"
    price = decode_netflix_value(info.get("planPrice")) or "N/A"
    hold_status = decode_netflix_value(info.get("holdStatus")) or "UNKNOWN"
    extra_member = "Yes" if is_extra else decode_netflix_value(info.get("showExtraMemberSection")) or "No"
    email_verified = decode_netflix_value(info.get("emailVerified")) or "UNKNOWN"
    membership_status = decode_netflix_value(info.get("membershipStatus")) or "UNKNOWN"

    profiles = info.get("profiles") or []
    if isinstance(profiles, str):
        profiles = [p.strip() for p in profiles.split(",") if p.strip()]
    profile_count = len(profiles)
    profiles_str = ", ".join(profiles) if profiles else "UNKNOWN"

    lines = [
        f"NETFLIX {status_text} :{status_emoji}",
        "",
        f"👤 Name: {name}",
        f"📧 Email: {email}",
        f"🌍 Country: {country_display}",
        f"📦 Plan: {plan_label}",
        f"📅 Member Since: {member_since}",
    ]

    if is_subscribed:
        lines += [
            f"🗓️ Next Billing: {next_billing}",
            f"💳 Payment: {payment}",
            f"📱 Phone: {phone}",
            f"🎞️ Quality: {quality}",
            f"📺 Streams: {streams}",
            f"💰 Price: {price}",
            f"⏸️ Hold Status: {hold_status}",
            f"👥 Extra Member: {extra_member}",
        ]

    lines += [
        f"✅ Email Verified: {email_verified}",
        f"🛡️ Membership Status: {membership_status}",
        f"🎭 Profiles ({profile_count}): {profiles_str}",
    ]

    return "\n".join(lines)
