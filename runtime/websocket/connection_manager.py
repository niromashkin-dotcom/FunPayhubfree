# runtime/websocket/connection_manager.py
import threading
from typing import Set

class ConnectionManager:
    def __init__(self):
        self._connections: Set = set()
        self._lock = threading.Lock()
        self._message_count = 0

    def register(self, client):
        with self._lock:
            self._connections.add(client)
            print(f"[WebSocket] Client connected. Total: {len(self._connections)}")

    def unregister(self, client):
        with self._lock:
            if client in self._connections:
                self._connections.remove(client)
                print(f"[WebSocket] Client disconnected. Total: {len(self._connections)}")

    def broadcast(self, payload):
        with self._lock:
            disconnected = []
            for client in self._connections:
                try:
                    client.send(payload)
                    self._message_count += 1
                except Exception as e:
                    print(f"[WebSocket] Send error: {e}")
                    disconnected.append(client)
            for d in disconnected:
                self.unregister(d)

    def get_clients_count(self):
        with self._lock:
            return len(self._connections)

    def get_message_count(self):
        return self._message_count