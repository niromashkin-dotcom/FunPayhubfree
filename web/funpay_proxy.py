"""
FunPay Hub - Profile proxy
Scrapes avatar + rating from funpay.com user page.
"""
from flask import Blueprint, jsonify, request, current_app
import re
import time

from runtime.http_client import HTTPClient, HTTPClientError

_http_client = HTTPClient(max_retries=3)

funpay_proxy_bp = Blueprint("funpay_proxy", __name__)

_cache = {}
_CACHE_TTL = 300


def _get_user_id_from_seller_service():
    """Try to extract user_id from various places."""
    # 1) Try via seller_service singleton
    try:
        from runtime.seller_service import seller_service_singleton as svc
        # method
        if hasattr(svc, "get_overview"):
            try:
                ov = svc.get_overview()
                if ov:
                    uid = ov.get("user_id") or ov.get("id") or ov.get("uid")
                    if uid: return str(uid)
            except Exception:
                pass
        # attributes
        for attr in ("user_id", "uid", "id"):
            if hasattr(svc, attr):
                v = getattr(svc, attr)
                if v: return str(v)
    except Exception:
        pass

    # 2) Try /api/seller/overview via internal call
    try:
        from bot.config import get_hub_url
        j = _http_client.get(f"{get_hub_url()}/api/seller/overview", timeout=3)
        uid = j.get("user_id") or j.get("id") or j.get("uid")
        if uid: return str(uid)
    except Exception:
        pass

    return None


def _scrape_profile(user_id: str) -> dict:
    url = f"https://funpay.com/users/{user_id}/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    try:
        html = _http_client.get(url, headers=headers, timeout=8)
    except HTTPClientError as e:
        return {"error": f"http {e.status_code}" if e.status_code else str(e.last_error), "user_id": user_id}
    except Exception as e:
        return {"error": str(e), "user_id": user_id}

    out = {
        "user_id": user_id,
        "profile_url": url,
        "rating": 0.0,        # ALWAYS return 0 if not found
        "reviews_count": 0,   # ALWAYS return 0 if not found
    }

    # Username - try multiple patterns
    name = None
    for pat in [
        r'<h1[^>]*class="[^"]*mb40[^"]*"[^>]*>\s*<span[^>]*>([^<]+)</span>',
        r'<span\s+class="mr4">([^<]+)</span>',
        r'<title>\s*([^<|]+?)\s*[|—-]',
    ]:
        m = re.search(pat, html)
        if m:
            name = m.group(1).strip()
            if name and name.lower() not in ("funpay", ""):
                out["username"] = name
                break

    # Avatar — multiple patterns
    avatar = None
    for pat in [
        r'<div[^>]*class="[^"]*avatar-photo[^"]*"[^>]*style="[^"]*url\(([^)]+)\)',
        r'<img[^>]*class="[^"]*avatar-photo[^"]*"[^>]*src="([^"]+)"',
        r'avatar-photo[^>]*style="[^"]*url\(([^)]+)\)',
    ]:
        m = re.search(pat, html)
        if m:
            avatar = m.group(1).strip().strip('\'"')
            if avatar.startswith("//"):
                avatar = "https:" + avatar
            elif avatar.startswith("/"):
                avatar = "https://funpay.com" + avatar
            out["avatar_url"] = avatar
            break

    # Rating
    for pat in [
        r'big-rating-mark[^>]*>\s*([\d.,]+)\s*<',
        r'class="rating-mark"[^>]*>\s*([\d.,]+)',
        r'data-rating="([\d.]+)"',
    ]:
        m = re.search(pat, html)
        if m:
            try:
                out["rating"] = float(m.group(1).replace(",", "."))
                break
            except Exception:
                pass

    # Reviews count
    for pat in [
        r'big-rating-count[^>]*>\s*(\d+)',
        r'rating-full-count[^>]*>\s*(\d+)',
        r'отзыв[а-я]*\s*[(\[]?\s*(\d+)\s*[)\]]?',
        r'(\d+)\s+отзыв',
    ]:
        m = re.search(pat, html)
        if m:
            try:
                out["reviews_count"] = int(m.group(1))
                break
            except Exception:
                pass

    # Online
    if re.search(r'media-user-status[^>]*>\s*[Оо]нлайн', html):
        out["online"] = True
    elif re.search(r'media-user-status', html):
        out["online"] = False

    return out


@funpay_proxy_bp.route("/api/funpay/profile/<user_id>")
def get_profile(user_id):
    now = time.time()
    cached = _cache.get(user_id)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return jsonify({"ok": True, "data": cached[1], "cached": True})

    data = _scrape_profile(user_id)
    if not data.get("error"):
        _cache[user_id] = (now, data)
    return jsonify({"ok": "error" not in data, "data": data})


@funpay_proxy_bp.route("/api/funpay/me")
def get_me():
    uid = _get_user_id_from_seller_service()
    if not uid:
        return jsonify({
            "ok": False,
            "error": "user_id not found",
            "hint": "make sure /api/seller/overview returns id or user_id"
        }), 404
    return get_profile(uid)


# Debug endpoint
@funpay_proxy_bp.route("/api/funpay/debug")
def debug():
    uid = _get_user_id_from_seller_service()
    return jsonify({
        "detected_user_id": uid,
        "cache_size": len(_cache),
    })