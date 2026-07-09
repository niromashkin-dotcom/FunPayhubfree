# runtime/notifications/channels/base_channel.py
from runtime.notifications.notification_types import Notification

class BaseChannel:
    def send(self, notification: Notification) -> bool:
        raise NotImplementedError