import urllib.parse
from flask import Flask, render_template, request, jsonify
import config
from netflix import parse_cookies, parse_cookie_blocks, get_login_links, probe_endpoint, split_cookie_blocks

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


@app.errorhandler(404)
def handle_404(err):
    """Trả HTML 404 thân thiện thay vì JSON, để user paste nhầm URL không thấy 'JSON error'."""
    return render_template(
        "index.html",
        title=config.APP_TITLE,
        subtitle=config.APP_SUBTITLE,
        missing="notfound",
    ), 404


@app.errorhandler(405)
def handle_405(err):
    return jsonify({"ok": False, "error": "Method không được phép"}), 405


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    # Không bắt HTTPException (Flask tự xử lý 404/405/etc) — nhưng ta vẫn cần convert
    # sang Response object đúng cách để status code không bị mất.
    from werkzeug.exceptions import HTTPException
    if isinstance(err, HTTPException):
        # Nếu là 404/405 và đã có handler riêng → Flask sẽ gọi handler đó trước, nên
        # code này chỉ chạy cho các HTTPException khác (400, 500 custom…).
        # Trả về response với code đúng.
        return err.get_response() if hasattr(err, "get_response") else (
            jsonify({"ok": False, "error": str(err)}), err.code or 500
        )
    app.logger.exception("Unhandled error")
    # Nếu request muốn JSON (API) → trả JSON
    if request.path.startswith("/api/") or request.path.startswith("/redeem"):
        return jsonify({"ok": False, "error": f"Lỗi server nội bộ: {type(err).__name__}"}), 500
    # Còn lại trả HTML
    return render_template(
        "index.html",
        title=config.APP_TITLE,
        subtitle=config.APP_SUBTITLE,
        missing="server",
    ), 500


def _attach_mobile_link(result: dict) -> dict:
    """Ghi đè field 'mobile' / 'app' / 'web' bằng URL phù hợp cho từng platform.

    URL outputs:
      - web:      https://www.netflix.com/?nftoken=<token>
                  Dùng cho iOS/PC — AASA exclude path "?" → mở Safari/Chrome → Netflix
                  web redeem token → login OK.
      - app:      https://www.netflix.com/unsupported?nftoken=<token>
                  Dùng cho Android — Netflix App Link claim path /unsupported → mở
                  app Netflix → app tự redeem token → login OK.
      - mobile:   alias backward-compat = app_url (link Netflix thuần, không qua
                  server). Khi user mở link này trực tiếp → Netflix mở app hoặc
                  web tùy platform, KHÔNG cần landing page trung gian.
    """
    if not (result.get("ok") and result.get("token")):
        return result
    token = result["token"]

    web_url = "https://www.netflix.com/?nftoken=" + urllib.parse.quote(token, safe="")
    app_url = "https://www.netflix.com/unsupported?nftoken=" + urllib.parse.quote(token, safe="")

    result["web"] = web_url
    result["app"] = app_url
    result["mobile"] = app_url
    return result


@app.route("/")
def index():
    missing = request.args.get("missing", "").strip()
    return render_template(
        "index.html",
        title=config.APP_TITLE,
        subtitle=config.APP_SUBTITLE,
        missing=missing,
    )


@app.route("/api/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    raw = body.get("cookies", "")
    # Defensive: chỉ chấp nhận string. Nếu user/attacker gửi None/list/int → 400
    # rõ ràng thay vì 500 AttributeError.
    if not isinstance(raw, str):
        return jsonify({
            "ok": False,
            "error": "Trường 'cookies' phải là chuỗi (string).",
        }), 400
    raw = raw.strip()
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
    raw_all = body.get("cookies", "")
    if not isinstance(raw_all, str):
        return jsonify({"ok": False, "error": "Trường 'cookies' phải là chuỗi."}), 400
    raw_all = raw_all.strip()
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
    raw_all = body.get("cookies", "")
    if not isinstance(raw_all, str):
        return jsonify({"ok": False, "error": "Trường 'cookies' phải là chuỗi."}), 400
    raw_all = raw_all.strip()
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
    raw = body.get("cookies", "")
    url = body.get("url", "")
    method = body.get("method", "POST").upper()

    if not isinstance(raw, str) or not isinstance(url, str):
        return jsonify({"error": "Trường 'cookies' và 'url' phải là chuỗi."}), 400
    raw = raw.strip()
    url = url.strip()

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
