from flask import Blueprint, jsonify, request, current_app, Response
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runtime.runtime_log import RuntimeLog, LogLevel

logs_bp = Blueprint("logs", __name__)
_runtime_log_singleton = RuntimeLog()


def _get_runtime_log():
    rl = getattr(current_app, "runtime_log", None)
    if rl is None:
        return _runtime_log_singleton
    return rl


def _get_observability():
    return getattr(current_app, "observability", None)


def _seed_demo_logs(rl):
    return


def _read_app_log(limit=200, level=None, source=None, search=None):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(root, "logs", "app.log")
    if not os.path.exists(log_path):
        return []
    entries = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        for line in lines[-limit * 2:]:
            line = line.strip()
            if not line:
                continue
            entries.append({"raw": line})
    except Exception:
        return []
    return entries[-limit:]


@logs_bp.route("/api/logs")
def list_logs():
    rl = _get_runtime_log()
    _seed_demo_logs(rl)
    level_str = request.args.get("level")
    source = request.args.get("source")
    search = request.args.get("q", "").lower()
    limit = int(request.args.get("limit", 200))
    level = None
    if level_str:
        try:
            level = LogLevel(level_str.upper())
        except Exception:
            level = None
    entries = rl.get_entries(level=level)
    if source:
        entries = [e for e in entries if source.lower() in e["source"].lower()]
    if search:
        entries = [e for e in entries if search in e.get("message", "").lower() or search in e.get("source", "").lower()]
    entries = entries[-limit:]

    file_entries = _read_app_log(limit=limit, level=level_str, source=source, search=search)
    if file_entries:
        for fe in file_entries:
            raw = fe.get("raw", "")
            if search and search not in raw.lower():
                continue
            entries.append({
                "time": "",
                "timestamp": 0,
                "level": "INFO",
                "source": "app.log",
                "message": raw,
            })

    entries.sort(key=lambda e: e.get("timestamp", 0) or 0)
    entries = entries[-limit:]
    return jsonify({"logs": entries, "count": len(entries)})


@logs_bp.route("/api/logs/stats")
def logs_stats():
    rl = _get_runtime_log()
    _seed_demo_logs(rl)
    entries = rl.get_entries()
    by_level = {"INFO": 0, "WARNING": 0, "ERROR": 0, "DEBUG": 0}
    sources = set()
    for e in entries:
        lvl = e.get("level", "INFO")
        by_level[lvl] = by_level.get(lvl, 0) + 1
        sources.add(e.get("source", ""))
    return jsonify({"total": len(entries), "by_level": by_level, "sources": sorted(list(sources))})


@logs_bp.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    rl = _get_runtime_log()
    rl.clear()
    return jsonify({"status": "cleared"})


@logs_bp.route("/api/logs/export")
def export_logs():
    rl = _get_runtime_log()
    entries = rl.get_entries()
    text_lines = []
    for e in entries:
        t = e.get("time", "")
        lv = e.get("level", "")
        sr = e.get("source", "")
        ms = e.get("message", "")
        text_lines.append("[" + t + "] [" + lv + "] [" + sr + "] " + ms)
    body = "\n".join(text_lines)
    return Response(body, mimetype="text/plain", headers={"Content-Disposition": "attachment; filename=runtime_logs.txt"})


@logs_bp.route("/api/logs/test", methods=["POST"])
def add_test_log():
    rl = _get_runtime_log()
    body = request.json or {}
    level_str = body.get("level", "INFO").upper()
    source = body.get("source", "manual")
    message = body.get("message", "Test log entry")
    try:
        level = LogLevel(level_str)
    except Exception:
        level = LogLevel.INFO
    rl.add(level, source, message)
    return jsonify({"status": "added"})


@logs_bp.route("/api/events")
def list_events():
    obs = _get_observability()
    if obs is None:
        return jsonify({"events": [], "count": 0, "live": False})
    limit = int(request.args.get("limit", 200))
    events = obs.get_event_history(limit=limit)
    return jsonify({"events": events, "count": len(events), "live": True})