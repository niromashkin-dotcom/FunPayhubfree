# runtime/notifications/channels/log_channel.py
from runtime.notifications.channels.base_channel import BaseChannel
from runtime.notifications.notification_types import Notification

class LogChannel(BaseChannel):
    def __init__(self, runtime_log):
        self.runtime_log = runtime_log

    def send(self, notification: Notification) -> bool:
        log_msg = f"[{notification.type.value.upper()}] {notification.title}: {notification.message}"
        if notification.type.value in ("error", "critical"):
            self.runtime_log.error("Notification", log_msg)
        else:
            self.runtime_log.info("Notification", log_msg)
        return True