# runtime/websocket/websocket_hub.py
import json
from runtime.websocket.connection_manager import ConnectionManager
from runtime.websocket.event_serializer import serialize_event
from runtime.event_types import Event

class WebSocketHub:
    def __init__(self, event_bus, runtime_log):
        self.event_bus = event_bus
        self.runtime_log = runtime_log
        self.connection_manager = ConnectionManager()
        self._running = True

        self.event_bus.subscribe("plugin_action", self._on_event)
        self.event_bus.subscribe("health_update", self._on_health_update)
        self.event_bus.subscribe("metrics_update", self._on_metrics_update)

        print("[WebSocketHub] Started, listening to EventBus")

    def broadcast_notification(self, notification):
        payload = json.dumps({
            "type": "notification",
            "data": notification.to_dict()
        })
        self.connection_manager.broadcast(payload)

    def _on_event(self, event: Event):
        if not self._running:
            return
        try:
            payload = serialize_event(event)
            self.connection_manager.broadcast(payload)
        except Exception as e:
            self.runtime_log.error("WebSocketHub", f"Broadcast error: {e}")

    def _on_health_update(self, data):
        if not self._running:
            return
        try:
            payload = json.dumps({
                "type": "health_update",
                "score": data.get("score"),
                "status": data.get("status")
            })
            self.connection_manager.broadcast(payload)
        except Exception as e:
            self.runtime_log.error("WebSocketHub", f"Health broadcast error: {e}")

    def _on_metrics_update(self, data):
        if not self._running:
            return
        try:
            payload = json.dumps({
                "type": "metrics_update",
                "plugin": data.get("plugin"),
                "metrics": data.get("metrics")
            })
            self.connection_manager.broadcast(payload)
        except Exception as e:
            self.runtime_log.error("WebSocketHub", f"Metrics broadcast error: {e}")

    def get_stats(self):
        return {
            "clients": self.connection_manager.get_clients_count(),
            "messages_sent": self.connection_manager.get_message_count()
        }

    def stop(self):
        self._running = False