PORT = 5000
DEBUG = False
SECRET_KEY = "n3tf1ix-l0g1n-4pp-2024-xK9mP2vL8wQ3hJ5nR7sT1uY6zA0bC4dE"

# --- Auth credentials (Basic Auth) ---
# Hiện tại không dùng — app public cho vài người dùng
import os
AUTH_USER = ""
AUTH_PASS = ""

# --- Tuỳ chỉnh tiêu đề hiển thị ---
APP_TITLE = "Netflix Login Link Generator"
APP_SUBTITLE = "Chuyển đổi Cookie Netflix thành Link Đăng Nhập"

# --- URL đăng nhập theo platform ---
#   PC / Web / iPad / Android → https://netflix.com/?nftoken=<token>  (root NO-WWW)
#   iPhone                    → https://netflix.com/unsupported?nftoken=  (GIỮ NHƯ CŨ theo yêu cầu)
#   Android (khách bấm link trong webview Zalo/Messenger) → <base_url>/r/<token>
#     (landing thoát webview ra trình duyệt thật rồi mở root ở đó)
#
# VÌ SAO ANDROID dùng root /?nftoken= chứ KHÔNG /unsupported — kiểm chứng LIVE 2026-08-08:
#   - AASA + assetlinks CHÍNH THỨC của Netflix: path "/unsupported" bị EXCLUDE khỏi AUTO app handoff
#     (Universal Link iOS lẫn App Link Android). App cướp link /unsupported → không route được →
#     render /NotFound = NSES-404. Root "/?*" thì ĐƯỢC claim + redeem sạch.
#   - iPhone GIỮ /unsupported: iPhone KHÔNG dính NSES-404 như Android; trên Safari, /unsupported
#     redeem token rồi hiện nút "Open App" (handoff thủ công) → OK. Fix lần này CHỈ nhắm Android.
#   - Probe token THẬT: mọi path đều redeem (set NetflixId); KHÔNG path nào trả NSES-404 phía server.
#     NSES-404 = app cướp link rồi mở path nó không route được (vd /unsupported) → tùy cấu hình MÁY
#     (có/không app + bật mở-link) → CHẬP CHỜN dù cùng account/quốc gia.
#   - Tool cộng đồng gốc (harshitkamboj / elakirihacker) chỉ xuất DUY NHẤT netflix.com/?nftoken=.
#   - Token là base64 CHUẨN (có +, /): GIỮ THÔ, KHÔNG url-encode (encode gây double-encode trong redirect).
# VÌ SAO NO-WWW (KHÔNG www) — kiểm chứng desktop UA 2026-08-08 + Playwright 2026-06-13:
#   - netflix.com/?nftoken= → 301 www.netflix.com/ (redeem + strip token) → /browse = ĐĂNG NHẬP OK.
#   - www.netflix.com/?nftoken= → token bị mang tiếp → /browse?nftoken= → /login = THẤT BẠI.
#   ⇒ TUYỆT ĐỐI giữ no-www (apex 301 mới redeem sạch).
# Token mint qua iOS FTL (ios.prod.ftl.netflix.com/iosui/user/15.48) — y hệt bot gốc.
LOGIN_BASE = "https://netflix.com/?nftoken="                         # DÙNG CHUNG cho mọi platform (NO-WWW)
# MOBILE_LOGIN_BASE sẽ được build runtime = base_url + /r/<encoded_token>
# → xem _build_result() trong netflix.py
# Giữ constant này rỗng để tương thích code cũ (sẽ tự dùng intermediary_url):
MOBILE_LOGIN_BASE = ""

# ─── ENDPOINT TUỲ CHỈNH ────────────────────────────────────────────────────
# Nếu bạn biết đúng endpoint Netflix, điền vào đây.
# Ví dụ: "https://www.netflix.com/api/shakti/v1db76858/loginWithToken"
# Để trống ("") để dùng danh sách endpoint tự động.
CUSTOM_ENDPOINT = ""

# --- User-Agent cho requests ---
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# --- Màu sắc theme (hex) ---
THEME_PRIMARY = "#E50914"
THEME_BG = "#141414"
THEME_CARD = "#1f1f1f"
