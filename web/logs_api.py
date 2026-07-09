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
    if rl.count() > 0:
        return
    rl.info("RuntimeController", "Система запущена")
    rl.info("PluginManager", "Загружено 4 плагина")
    rl.warning("AutoResponse", "Низкая скорость ответа")
    rl.error("NewMessageView", "Не удалось подключиться к серверу")
    rl.info("AutoDelivery", "Обработано 12 заказов")
    rl.debug("EventBus", "Подписчик зарегистрирован: dashboard")


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
        entries = [e for e in entries if search in e["message"].lower() or search in e["source"].lower()]
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