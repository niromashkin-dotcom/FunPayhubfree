# runtime/observability/event_store.py
from collections import deque
from typing import List, Optional
from runtime.event_types import Event, EventSeverity


class EventStore:
    def __init__(self, max_size: int = 1000):
        self._events: deque = deque(maxlen=max_size)

    def add(self, event: Event):
        self._events.append(event)

    def get_all(self) -> List[Event]:
        return list(self._events)

    def get_by_correlation(self, correlation_id: str) -> List[Event]:
        return [e for e in self._events if e.correlation_id == correlation_id]

    def get_by_plugin(self, plugin_name: str) -> List[Event]:
        return [e for e in self._events if e.plugin == plugin_name]

    def get_by_severity(self, severity: EventSeverity) -> List[Event]:
        return [e for e in self._events if e.severity == severity]

    def get_errors(self) -> List[Event]:
        return self.get_by_severity(EventSeverity.ERROR)

    def clear(self):
        self._events.clear()

    def size(self) -> int:
        return len(self._events)

    def get_stats(self) -> dict:
        total = len(self._events)
        errors = len(self.get_errors())
        return {
            "total": total,
            "errors": errors,
            "error_rate": errors / total if total > 0 else 0
        }