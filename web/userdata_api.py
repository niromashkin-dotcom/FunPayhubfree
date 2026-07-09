"""
FunPay Hub - User Data API
Handles uploads of custom backgrounds, sounds, theme files.
Stored in /userdata/ relative to the EXE or main script (survives rebuilds).
"""
from flask import Blueprint, request, jsonify, send_from_directory, abort
import sys, os, uuid, hashlib
from pathlib import Path

userdata_bp = Blueprint("userdata", __name__)

# ----------------------------------------------------------------------------
# Resolve userdata directory:
#   - frozen (.exe): next to the .exe
#   - dev (python): project root next to funpayhub_main.py
# ----------------------------------------------------------------------------

def _userdata_root() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        # Walk up from this file to find project root with funpayhub_main.py
        here = Path(__file__).resolve()
        for parent in [here.parent.parent, here.parent.parent.parent]:
            if (parent / "funpayhub_main.py").exists():
                return parent / "userdata"
        base = here.parent.parent
    return base / "userdata"


USERDATA = _userdata_root()
USERDATA.mkdir(parents=True, exist_ok=True)
(USERDATA / "backgrounds").mkdir(exist_ok=True)
(USERDATA / "sounds").mkdir(exist_ok=True)
(USERDATA / "themes").mkdir(exist_ok=True)


ALLOWED = {
    "background": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"},
    "sound":      {".mp3", ".wav", ".ogg", ".m4a"},
}
MAX_BYTES = {
    "background": 100 * 1024 * 1024,  # 100 MB (videos allowed)
    "sound":      10  * 1024 * 1024,  # 10 MB
}


def _safe_filename(original: str, content: bytes) -> str:
    """Generate a deterministic safe filename based on content hash."""
    ext = Path(original).suffix.lower()
    h = hashlib.sha1(content).hexdigest()[:16]
    return f"{h}{ext}"


@userdata_bp.route("/api/userdata/upload", methods=["POST"])
def upload():
    """
    POST multipart/form-data:
        file: <binary>
        type: "background" | "sound"

    Returns:
        { "ok": true, "url": "/userdata/backgrounds/abc123.jpg", "name": "abc123.jpg" }
    """
    kind = (request.form.get("type") or "").strip().lower()
    if kind not in ALLOWED:
        return jsonify({"ok": False, "error": "invalid type"}), 400

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no file"}), 400

    f = request.files["file"]
    raw = f.read()

    if len(raw) == 0:
        return jsonify({"ok": False, "error": "empty file"}), 400
    if len(raw) > MAX_BYTES[kind]:
        return jsonify({"ok": False, "error": f"file too large (max {MAX_BYTES[kind] // 1024 // 1024} MB)"}), 400

    ext = Path(f.filename or "").suffix.lower()
    if ext not in ALLOWED[kind]:
        return jsonify({"ok": False, "error": f"extension {ext} not allowed"}), 400

    fname = _safe_filename(f.filename or "upload", raw)
    subdir = "backgrounds" if kind == "background" else "sounds"
    target = USERDATA / subdir / fname

    try:
        target.write_bytes(raw)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({
        "ok":   True,
        "url":  f"/userdata/{subdir}/{fname}",
        "name": fname,
        "size": len(raw),
        "type": kind,
    })


@userdata_bp.route("/api/userdata/list", methods=["GET"])
def list_files():
    kind = (request.args.get("type") or "").strip().lower()
    if kind not in ALLOWED:
        return jsonify({"ok": False, "error": "invalid type"}), 400
    subdir = "backgrounds" if kind == "background" else "sounds"
    folder = USERDATA / subdir
    if not folder.exists():
        return jsonify({"ok": True, "files": []})
    files = []
    for p in folder.iterdir():
        if p.is_file() and not p.name.startswith("."):
            files.append({
                "name": p.name,
                "url":  f"/userdata/{subdir}/{p.name}",
                "size": p.stat().st_size,
            })
    return jsonify({"ok": True, "files": files})


@userdata_bp.route("/api/userdata/delete", methods=["POST"])
def delete():
    body = request.json or {}
    kind = (body.get("type") or "").strip().lower()
    name = (body.get("name") or "").strip()
    if kind not in ALLOWED or not name:
        return jsonify({"ok": False, "error": "invalid params"}), 400
    # safety: forbid path traversal
    if "/" in name or "\\" in name or ".." in name:
        return jsonify({"ok": False, "error": "invalid name"}), 400
    subdir = "backgrounds" if kind == "background" else "sounds"
    target = USERDATA / subdir / name
    if target.exists() and target.is_file():
        try:
            target.unlink()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": False, "error": "not found"}), 404


@userdata_bp.route("/userdata/<path:filename>")
def serve_userdata(filename):
    # safety: forbid path traversal
    if ".." in filename:
        abort(403)
    return send_from_directory(str(USERDATA), filename)