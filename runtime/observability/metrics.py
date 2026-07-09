# runtime/observability/metrics.py
import time
from collections import defaultdict
from typing import Dict


class PluginMetrics:
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.total_events = 0
        self.error_count = 0
        self.warning_count = 0
        self.last_event_time = 0
        self.uptime_start = 0
        self.restart_count = 0
        self.state_changes = 0

    def record_event(self, severity: str):
        self.total_events += 1
        self.last_event_time = time.time()
        if severity == "error":
            self.error_count += 1
        elif severity == "warning":
            self.warning_count += 1

    def record_state_change(self):
        self.state_changes += 1

    def record_restart(self):
        self.restart_count += 1

    def set_uptime_start(self):
        self.uptime_start = time.time()

    def get_uptime(self) -> float:
        return time.time() - self.uptime_start if self.uptime_start else 0

    def get_stability_score(self) -> float:
        score = 100 - (self.error_count * 10 + self.restart_count * 5)
        return max(0, min(100, score))

    def to_dict(self) -> dict:
        return {
            "plugin": self.plugin_name,
            "total_events": self.total_events,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "last_event_time": self.last_event_time,
            "uptime": self.get_uptime(),
            "restarts": self.restart_count,
            "state_changes": self.state_changes,
            "stability_score": self.get_stability_score()
        }


class MetricsCollector:
    def __init__(self):
        self._metrics: Dict[str, PluginMetrics] = {}

    def get_or_create(self, plugin_name: str) -> PluginMetrics:
        if plugin_name not in self._metrics:
            self._metrics[plugin_name] = PluginMetrics(plugin_name)
        return self._metrics[plugin_name]

    def record_event(self, plugin_name: str, severity: str):
        self.get_or_create(plugin_name).record_event(severity)

    def record_state_change(self, plugin_name: str):
        self.get_or_create(plugin_name).record_state_change()

    def record_restart(self, plugin_name: str):
        self.get_or_create(plugin_name).record_restart()

    def set_uptime_start(self, plugin_name: str):
        self.get_or_create(plugin_name).set_uptime_start()

    def get_all_metrics(self) -> Dict[str, dict]:
        return {name: m.to_dict() for name, m in self._metrics.items()}

    def get_plugin_metrics(self, plugin_name: str) -> dict:
        m = self._metrics.get(plugin_name)
        return m.to_dict() if m else None

    def get_summary(self) -> dict:
        total_events = sum(m.total_events for m in self._metrics.values())
        total_errors = sum(m.error_count for m in self._metrics.values())
        avg_stability = sum(m.get_stability_score() for m in self._metrics.values()) / len(self._metrics) if self._metrics else 100
        return {
            "total_plugins": len(self._metrics),
            "total_events": total_events,
            "total_errors": total_errors,
            "average_stability": round(avg_stability, 1)
        }