# runtime/notifications/notification_rules.py
from runtime.notifications.notification_types import Notification, NotificationType
import time

class NotificationRules:
    def __init__(self):
        self._restart_counts = {}
        self._last_health = None

    def evaluate_event(self, event_dict) -> list:
        notifications = []
        action = event_dict.get("action")
        plugin = event_dict.get("plugin")
        result = event_dict.get("result")
        severity = event_dict.get("severity")
        source = event_dict.get("source", "eventbus")

        if action == "enable" and result == "failed":
            notifications.append(Notification(
                type=NotificationType.ERROR,
                title=f"Plugin {plugin} failed to enable",
                message=f"Action: {action}, result: {result}",
                source=source
            ))

        if action == "restart" and result == "success":
            key = f"restart_{plugin}"
            now = time.time()
            if key not in self._restart_counts:
                self._restart_counts[key] = []
            self._restart_counts[key] = [t for t in self._restart_counts[key] if now - t < 3600]
            self._restart_counts[key].append(now)
            if len(self._restart_counts[key]) > 5:
                notifications.append(Notification(
                    type=NotificationType.WARNING,
                    title=f"Plugin {plugin} restarted {len(self._restart_counts[key])} times in last hour",
                    message="Too many restarts, investigate stability",
                    source="notification_rules"
                ))

        if severity == "error":
            notifications.append(Notification(
                type=NotificationType.ERROR,
                title=f"Error in {plugin or 'system'}",
                message=event_dict.get("message", "No message"),
                source=source
            ))

        return notifications

    def evaluate_health(self, health_score, health_status) -> list:
        notifications = []
        if self._last_health is None:
            self._last_health = (health_score, health_status)
            return []
        old_score, old_status = self._last_health
        self._last_health = (health_score, health_status)

        if health_score < 50 and old_score >= 50:
            notifications.append(Notification(
                type=NotificationType.CRITICAL,
                title="System Health CRITICAL",
                message=f"Health score dropped to {health_score} ({health_status})",
                source="health_engine"
            ))
        elif health_score < 75 and old_score >= 75:
            notifications.append(Notification(
                type=NotificationType.WARNING,
                title="System Health Degraded",
                message=f"Health score is {health_score} ({health_status})",
                source="health_engine"
            ))
        return notifications