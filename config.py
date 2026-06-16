PORT = 5000
DEBUG = False
SECRET_KEY = "netflix-login-app-2024"

# --- Tuỳ chỉnh tiêu đề hiển thị ---
APP_TITLE = "Netflix Login Link Generator"
APP_SUBTITLE = "Chuyển đổi Cookie Netflix thành Link Đăng Nhập"

# --- URL đăng nhập ---
# 1 LINK DUY NHẤT cho mọi thiết bị = netflix.com/?nftoken=  (GIỐNG HỆT neogkey.com — đã verify
#   bằng cách decode link thật của họ: link Android của họ cũng là /?nftoken=, KHÔNG phải /unsupported).
# Token nftoken là DEVICE-AGNOSTIC (đã thực nghiệm: mọi device param đều ra token y hệt cho 1 account).
# LUỒNG ANDROID (theo neogkey, app native login ĐƯỢC):
#   paste link vào Chrome → trang Netflix → bấm "Open App" → trong app bấm "Continue" → login app.
#   Đây là OAuth handoff; CHẠY khi token còn tươi (<59') + account không bị household-lock.
#   NSES-404 (error=NoAuthSession) xảy ra khi token hết hạn/đã dùng/account lỗi.
LOGIN_BASE = "https://netflix.com/?nftoken="
PC_LOGIN_BASE = LOGIN_BASE
MOBILE_LOGIN_BASE = LOGIN_BASE

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
