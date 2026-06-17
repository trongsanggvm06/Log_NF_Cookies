from flask import Flask, render_template, request, jsonify, url_for
import urllib.parse
import config
from netflix import (
    parse_cookies,
    parse_cookie_blocks,
    get_login_links,
    refresh_cookies,
    probe_endpoint,
    split_cookie_blocks,
    _extract_dt,
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


def _get_base_url() -> str:
    """
    Lấy URL gốc của server đang host (vd "https://autologin-nf.onrender.com").
    Dùng để build intermediary URL trong response của /api/generate.
    Ưu tiên:
      1. Environment variable PUBLIC_BASE_URL (nếu deploy manual config)
      2. request.host_url (tự detect từ request, vd "http://127.0.0.1:5000/")
    """
    import os
    env_base = os.environ.get("PUBLIC_BASE_URL", "").strip()
    if env_base:
        return env_base.rstrip("/")
    # request.host_url luôn có trailing slash, vd "https://example.com/"
    return request.host_url.rstrip("/")


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    return jsonify({"ok": False, "error": f"Lỗi server nội bộ: {type(err).__name__}"}), 500


@app.route("/")
def index():
    return render_template("index.html", title=config.APP_TITLE, subtitle=config.APP_SUBTITLE)


# Trang trung gian: khi user mở link HTTPS này trên Android, JS sẽ hiện nút
# "Mở Netflix App" bấm vào sẽ fire intent:// → Chrome mở com.netflix.mediaclient.
# Trên iOS Safari tự nhận Universal Link → mở app luôn.
# Trên PC redirect thẳng tới web Netflix.
# Dùng <path:token> để capture cả dấu / có trong token (token Netflix chứa cả + và /).
# Token trong URL phải được URL-encoded (safe="" để giữ nguyên /) — khi browser mở
# link thì tự decode lại thành token gốc.
@app.route("/r/<path:token>")
def redirect_intermediary(token):
    # Flask đã tự URL-decode token rồi (dấu + thành space, %2B vẫn là +).
    # Để chắc chắn token còn nguyên vẹn, ta chỉ cần dùng nó trực tiếp trong HTML.
    # Token chỉ có thời hạn ~59 phút (1 giờ của Netflix). Hiển thị countdown.
    return render_template(
        "redirect.html",
        nftoken=token,
        expiry_min=59,
    )


@app.route("/api/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    raw = body.get("cookies", "").strip()
    if not raw:
        return jsonify({"ok": False, "error": "Vui lòng nhập cookie"}), 400

    parsed_blocks = parse_cookie_blocks(raw)
    cookies_dict = parsed_blocks[0] if parsed_blocks else parse_cookies(raw)
    if not cookies_dict:
        blocks = split_cookie_blocks(raw)
        if len(blocks) > 1:
            return jsonify({
                "ok": False,
                "error": (f"Bạn paste {len(blocks)} bộ cookie nhưng đang ở tab Đơn lẻ "
                          f"(chỉ xử lý 1). Hãy chuyển sang tab 📦 Batch."),
                "suggest_tab": "tab-batch",
                "count": len(blocks),
            }), 400
        return jsonify({"ok": False, "error": "Không thể đọc cookie, kiểm tra định dạng"}), 400
    result = get_login_links(cookies_dict, base_url=_get_base_url())
    return jsonify(result)


@app.route("/api/refresh-cookies", methods=["POST"])
def refresh_cookies_endpoint():
    body = request.get_json(silent=True) or {}
    raw = body.get("cookies", "").strip()
    if not raw:
        return jsonify({"ok": False, "error": "Vui lòng nhập cookie"}), 400

    cookies_dict = parse_cookies(raw)
    if not cookies_dict:
        return jsonify({"ok": False, "error": "Không đọc được cookie"}), 400

    old_dt = _extract_dt(cookies_dict.get("SecureNetflixId", ""))
    refreshed = refresh_cookies(cookies_dict)
    new_dt = _extract_dt(refreshed.get("SecureNetflixId", ""))
    refreshed_ok = refreshed.get("_refreshed", False)
    refresh_error = refreshed.get("_refresh_error")

    return jsonify({
        "ok": refreshed_ok,
        "error": refresh_error,
        "old_dt": old_dt,
        "new_dt": new_dt,
        "cookies": {k: v for k, v in refreshed.items() if not k.startswith("_")},
    })


@app.route("/api/split", methods=["POST"])
def split():
    body = request.get_json(silent=True) or {}
    raw_all = body.get("cookies", "").strip()
    if not raw_all:
        return jsonify({"ok": False, "error": "Vui lòng nhập cookie"}), 400

    parsed_blocks = parse_cookie_blocks(raw_all)
    if parsed_blocks:
        hydrated_blocks = []
        for cookie_dict in parsed_blocks:
            parts = []
            for key in ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn"):
                value = cookie_dict.get(key)
                if value:
                    parts.append(f"{key}={value}")
            if parts:
                hydrated_blocks.append("; ".join(parts))
        if hydrated_blocks:
            return jsonify({"ok": True, "blocks": hydrated_blocks, "count": len(hydrated_blocks)})

    blocks = split_cookie_blocks(raw_all)
    return jsonify({"ok": True, "blocks": blocks, "count": len(blocks)})


@app.route("/api/debug", methods=["POST"])
def debug():
    body = request.get_json(silent=True) or {}
    raw = body.get("cookies", "").strip()
    url = body.get("url", "").strip()
    method = body.get("method", "POST").upper()

    if not raw:
        return jsonify({"error": "Cần cookie"}), 400
    if not url:
        return jsonify({"error": "Cần url"}), 400

    cookies_dict = parse_cookies(raw)
    if not cookies_dict:
        return jsonify({"error": "Cookie không hợp lệ"}), 400

    result = probe_endpoint(cookies_dict, url, method)
    return jsonify(result)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", config.PORT))
    print(f"[*] App chạy tại http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=config.DEBUG)
