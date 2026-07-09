# runtime/notifications/channels/discord_channel.py
from datetime import datetime
from runtime.http_client import HTTPClient, HTTPClientError
from runtime.notifications.channels.base_channel import BaseChannel
from runtime.notifications.notification_types import Notification

class DiscordChannel(BaseChannel):
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.http_client = HTTPClient(max_retries=3)

    def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            return False
        color = {
            "info": 0x3498db,
            "success": 0x2ecc71,
            "warning": 0xf1c40f,
            "error": 0xe67e22,
            "critical": 0xe74c3c
        }.get(notification.type.value, 0x95a5a6)
        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": f"Source: {notification.source}"}
        }
        data = {"embeds": [embed]}
        try:
            self.http_client.post(self.webhook_url, json=data, timeout=5)
            return True
        except Exception as e:
            print(f"[DiscordChannel] Error: {e}")
            return False