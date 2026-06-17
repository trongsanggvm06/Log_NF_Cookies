PORT = 5000
DEBUG = False
SECRET_KEY = "netflix-login-app-2024"

# --- Tuỳ chỉnh tiêu đề hiển thị ---
APP_TITLE = "Netflix Login Link Generator"
APP_SUBTITLE = "Chuyển đổi Cookie Netflix thành Link Đăng Nhập"

# --- URL đăng nhập — GIỐNG HỆT logic Netflix-Cookie-Checker-main/bot.py:1022-1023 ---
#   pc_link     = https://netflix.com/?nftoken=<token>            → PC / Web / iPhone / iPad
#   mobile_link = https://netflix.com/unsupported?nftoken=<token> → Android
# Token mint qua iOS FTL (ios.prod.ftl.netflix.com/iosui/user/15.48) — y hệt bot gốc.
LOGIN_BASE = "https://netflix.com/?nftoken="                         # PC / Web / iPhone / iPad
PC_LOGIN_BASE = LOGIN_BASE
MOBILE_LOGIN_BASE = "https://netflix.com/unsupported?nftoken="       # Android

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
