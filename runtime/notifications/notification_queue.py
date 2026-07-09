# runtime/notifications/notification_queue.py
from collections import deque
import threading
from typing import List

class NotificationQueue:
    def __init__(self, max_size=1000):
        self._queue = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add(self, notification_dict):
        with self._lock:
            self._queue.append(notification_dict)

    def get_all(self) -> List:
        with self._lock:
            return list(self._queue)

    def get_last(self, limit: int = 50) -> List:
        with self._lock:
            return list(self._queue)[-limit:]

    def clear(self):
        with self._lock:
            self._queue.clear()

    def count(self):
        with self._lock:
            return len(self._queue)