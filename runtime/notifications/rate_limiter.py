# runtime/notifications/rate_limiter.py
import time
from collections import defaultdict
from typing import Dict, List

class RateLimiter:
    def __init__(self, max_per_minute: int = 10):
        self.max_per_minute = max_per_minute
        self._records: Dict[str, List[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        self._records[key] = [t for t in self._records[key] if now - t < 60]
        if len(self._records[key]) >= self.max_per_minute:
            return False
        self._records[key].append(now)
        return True