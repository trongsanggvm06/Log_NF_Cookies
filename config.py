PORT = 5000
DEBUG = False
SECRET_KEY = "netflix-login-app-2024"

# --- Tuỳ chỉnh tiêu đề hiển thị ---
APP_TITLE = "Netflix Login Link Generator"
APP_SUBTITLE = "Chuyển đổi Cookie Netflix thành Link Đăng Nhập"

# --- URL đăng nhập ---
# PC  : netflix.com/?nftoken=  → desktop redeem → /browse (login web).
# MOBILE: netflix.com/unsupported?nftoken=  → đường /unsupported app Netflix KHÔNG claim
#   (iOS AASA exclude; Android tương tự) → tap từ chat KHÔNG bị app cướp → ở lại trình duyệt →
#   token redeem (login web). Tránh được CẢ 3 lỗi: NSES-404 (/oAuth2Login), nhảy màn app-login,
#   và kẹt màn login. Lưu ý: app NATIVE không login được bằng nftoken (token là của WEB);
#   muốn XEM trên điện thoại, khách bật "Request Desktop Site".
LOGIN_BASE = "https://netflix.com/?nftoken="
PC_LOGIN_BASE = LOGIN_BASE
MOBILE_LOGIN_BASE = "https://netflix.com/unsupported?nftoken="

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
