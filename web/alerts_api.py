from flask import Blueprint, jsonify, request, current_app
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runtime.notifications.notification_manager import NotificationManager
from runtime.notifications.notification_types import Notification, NotificationType

alerts_bp = Blueprint("alerts", __name__)
_manager_singleton = NotificationManager()


def _get_manager():
    nm = getattr(current_app, "notification_manager", None)
    if nm is None:
        return _manager_singleton
    return nm


@alerts_bp.route("/api/alerts")
def list_alerts():
    nm = _get_manager()
    level = request.args.get("level")
    source = request.args.get("source")
    only_unack = request.args.get("only_unack", "false").lower() == "true"
    limit = int(request.args.get("limit", 200))
    items = []
    items = items[-limit:]
    return jsonify({"alerts": items, "count": len(items)})


@alerts_bp.route("/api/alerts/stats")
def alerts_stats():
    nm = _get_manager()
    return jsonify({"total": 0, "unread": 0})


@alerts_bp.route("/api/alerts/<alert_id>/ack", methods=["POST"])
def ack_alert(alert_id):
    nm = _get_manager()
    ok = nm.acknowledge(alert_id)
    if not ok:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"status": "acknowledged", "id": alert_id})


@alerts_bp.route("/api/alerts/<alert_id>/dismiss", methods=["POST"])
def dismiss_alert(alert_id):
    nm = _get_manager()
    ok = nm.dismiss(alert_id)
    if not ok:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"status": "dismissed", "id": alert_id})


@alerts_bp.route("/api/alerts/clear", methods=["POST"])
def clear_alerts():
    nm = _get_manager()
    nm.clear_history()
    return jsonify({"status": "cleared"})


@alerts_bp.route("/api/alerts/test", methods=["POST"])
def create_test_alert():
    nm = _get_manager()
    body = request.json or {}
    level = body.get("level", "info")
    try:
        ntype = NotificationType(level)
    except Exception:
        ntype = NotificationType.INFO
    n = Notification(
        type=ntype,
        title=body.get("title", "Test alert"),
        message=body.get("message", "This is a test alert"),
        source=body.get("source", "manual")
    )
    nm.send(n)
    return jsonify({"status": "sent", "id": n.id})