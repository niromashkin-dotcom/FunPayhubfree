# plugins/health_score.py
import time
from collections import deque
from typing import Optional

class PluginHealthScore:
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        # Скользящие окна (последние 60 секунд)
        self._latency_history = deque(maxlen=60)   # секунды
        self._error_history = deque(maxlen=60)     # 1 – была ошибка в эту секунду
        self._restart_history = deque(maxlen=60)   # 1 – был рестарт в эту секунду
        self._event_history = deque(maxlen=60)     # количество событий в секунду

    def update_latency(self, duration: float):
        self._latency_history.append(duration)

    def update_error(self):
        self._error_history.append(1)

    def update_restart(self):
        self._restart_history.append(1)

    def update_event_count(self, count: int = 1):
        self._event_history.append(count)

    def tick(self):
        """Вызывается раз в секунду для продвижения окон (автоматически через maxlen)"""
        pass  # deque сам выталкивает старые

    def calculate_score(self) -> int:
        # 1. Latency penalty (среднее за 60 секунд)
        if self._latency_history:
            avg_latency = sum(self._latency_history) / len(self._latency_history)
        else:
            avg_latency = 0
        latency_penalty = min(30, avg_latency * 10)   # 1с -> -10, 3с -> -30

        # 2. Error rate (ошибки в секунду)
        total_errors = sum(self._error_history)
        error_rate = total_errors / max(1, len(self._error_history))
        error_penalty = min(30, error_rate * 20)      # 1 ошибка/сек -> -20

        # 3. Restart rate (рестарты в секунду)
        total_restarts = sum(self._restart_history)
        restart_rate = total_restarts / max(1, len(self._restart_history))
        restart_penalty = min(20, restart_rate * 10)

        # 4. Event spam (события/сек)
        total_events = sum(self._event_history)
        event_rate = total_events / max(1, len(self._event_history))
        max_allowed_rate = 10
        if event_rate > max_allowed_rate:
            spam_penalty = min(20, (event_rate - max_allowed_rate) * 2)
        else:
            spam_penalty = 0

        base = 100
        score = base - latency_penalty - error_penalty - restart_penalty - spam_penalty
        return max(0, min(100, int(score)))