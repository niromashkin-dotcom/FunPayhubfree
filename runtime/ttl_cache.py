import threading
import time
from collections import deque


class TTLSet:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._data = {}
        self._queue = deque()
        self._lock = threading.Lock()

    def add(self, item):
        with self._lock:
            now = time.time()
            self._data[item] = now
            self._queue.append((now, item))
            self._cleanup(now)

    def __contains__(self, item):
        with self._lock:
            now = time.time()
            self._cleanup(now)
            return item in self._data

    def discard(self, item):
        with self._lock:
            self._data.pop(item, None)

    def _cleanup(self, now):
        while self._queue and now - self._queue[0][0] > self.ttl_seconds:
            _, item = self._queue.popleft()
            self._data.pop(item, None)
