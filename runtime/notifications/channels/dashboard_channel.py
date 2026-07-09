# runtime/notifications/channels/dashboard_channel.py
import json
from runtime.notifications.channels.base_channel import BaseChannel
from runtime.notifications.notification_types import Notification

class DashboardChannel(BaseChannel):
    def __init__(self, websocket_hub):
        self.websocket_hub = websocket_hub

    def send(self, notification: Notification) -> bool:
        if not self.websocket_hub:
            return False
        self.websocket_hub.broadcast_notification(notification)
        return True