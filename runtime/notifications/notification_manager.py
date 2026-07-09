# runtime/notifications/notification_manager.py
from runtime.notifications.notification_types import Notification
from runtime.notifications.notification_queue import NotificationQueue
from runtime.notifications.rate_limiter import RateLimiter
from runtime.notifications.notification_rules import NotificationRules

class NotificationManager:
    def __init__(self):
        self._channels = []
        self._queue = NotificationQueue()
        self._rate_limiter = RateLimiter(max_per_minute=10)
        self._rules = NotificationRules()

    def register_channel(self, channel):
        self._channels.append(channel)

    def subscribe_to_event_bus(self, event_bus):
        self.event_bus = event_bus
        event_bus.subscribe("plugin_action", self._on_event)
        event_bus.subscribe("health_update", self._on_health_update)

    def _on_event(self, event):
        event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
        notifications = self._rules.evaluate_event(event_dict)
        for n in notifications:
            self.send(n)

    def _on_health_update(self, data):
        notifications = self._rules.evaluate_health(data.get("score"), data.get("status"))
        for n in notifications:
            self.send(n)

    def send(self, notification: Notification):
        key = f"{notification.source}:{notification.type.value}"
        if not self._rate_limiter.allow(key):
            return
        notif_dict = notification.to_dict()
        self._queue.add(notif_dict)
        for channel in self._channels:
            try:
                channel.send(notification)
            except Exception as e:
                print(f"[NotificationManager] Channel error: {e}")

    def get_history(self, limit=100):
        return self._queue.get_last(limit)

    def clear_history(self):
        self._queue.clear()