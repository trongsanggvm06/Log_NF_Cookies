import urllib.parse
from flask import Flask, render_template, request, jsonify
import config
from netflix import parse_cookies, parse_cookie_blocks, get_login_links, probe_endpoint, split_cookie_blocks

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    return jsonify({"ok": False, "error": f"Lỗi server nội bộ: {type(err).__name__}"}), 500


def _build_mobile_link(token: str) -> str:
    """
    Link mobile = landing page /go TRÊN CHÍNH server này (KHÔNG phải netflix.com).
    Lý do: gửi thẳng netflix.com/?nftoken= thì máy có app Netflix sẽ bị App Link/Universal Link
    cướp link -> app đẩy sang endpoint chết /oAuth2Login -> NSES-404 "Lost your way".
    Mở qua /go (domain khác netflix) thì app KHÔNG cướp; trang /go tự điều hướng sang netflix.com
    NGAY TRONG trình duyệt (điều hướng nội-trình-duyệt không kích App Link) -> redeem web chạy đúng.
    """
    host = request.host  # vd: myapp.onrender.com
    # Render/host thường terminate TLS upstream -> ép https cho host không phải local
    scheme = "http" if host.startswith(("127.", "localhost", "0.0.0.0")) else "https"
    return f"{scheme}://{host}/go?t=" + urllib.parse.quote(token, safe="")


def _attach_mobile_link(result: dict) -> dict:
    """Ghi đè field 'mobile' bằng URL /go nếu generate thành công."""
    if result.get("ok") and result.get("token"):
        result["mobile"] = _build_mobile_link(result["token"])
    return result


@app.route("/")
def index():
    return render_template("index.html", title=config.APP_TITLE, subtitle=config.APP_SUBTITLE)


@app.route("/go")
def go():
    """Landing page trung gian cho mobile: né app-intercept rồi redeem nftoken trong trình duyệt."""
    token = request.args.get("t", "").strip()
    if not token:
        return "Thiếu token đăng nhập.", 400
    return render_template("go.html", token=token, pc_base=config.LOGIN_BASE)


@app.route("/api/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    raw = body.get("cookies", "").strip()
    if not raw:
        return jsonify({"ok": False, "error": "Vui lòng nhập cookie"}), 400

    parsed_blocks = parse_cookie_blocks(raw)
    cookies_dict = parsed_blocks[0] if parsed_blocks else parse_cookies(raw)
    if not cookies_dict:
        # Có thể user paste nhiều bộ cookie vào tab Đơn lẻ → gợi ý chuyển Batch
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
    result = _attach_mobile_link(get_login_links(cookies_dict))
    return jsonify(result)


@app.route("/api/batch", methods=["POST"])
def batch():
    """Batch xử lý toàn bộ trong 1 request (legacy — vẫn giữ để compat)."""
    import time
    import random
    body = request.get_json(silent=True) or {}
    raw_all = body.get("cookies", "").strip()
    if not raw_all:
        return jsonify({"ok": False, "error": "Vui lòng nhập cookie"}), 400
    blocks = split_cookie_blocks(raw_all)
    parsed_blocks = parse_cookie_blocks(raw_all)
    results = []
    for i, block in enumerate(blocks, 1):
        cookies_dict = parsed_blocks[i - 1] if i - 1 < len(parsed_blocks) else parse_cookies(block)
        if not cookies_dict:
            results.append({"index": i, "ok": False, "error": "Không đọc được cookie"})
            continue
        result = _attach_mobile_link(get_login_links(cookies_dict))
        result["index"] = i
        results.append(result)
        if i < len(blocks):
            time.sleep(random.uniform(1.0, 3.0))
    return jsonify({"results": results})


@app.route("/api/split", methods=["POST"])
def split():
    """Tách input thành các block cookie đã được hydrate để frontend xử lý progressive batch ổn định hơn."""
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
    """
    Thử một endpoint tuỳ ý với cookie của bạn.
    Body: { "cookies": "...", "url": "https://...", "method": "POST" }
    Trả về raw response để giúp tìm endpoint đúng.
    """
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
    print(f"[*] Debug endpoint: POST http://0.0.0.0:{port}/api/debug")
    app.run(host="0.0.0.0", port=port, debug=config.DEBUG)
