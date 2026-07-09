# eventbus.py
import threading
from typing import Dict, List, Callable, Any
from collections import defaultdict


class EventBus:
    """Единая шина событий системы. Только диспетчеризация, без хранения."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable, priority=0) -> None:
        with self._lock:
            if handler not in self._listeners[event_type]:
                self._listeners[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        with self._lock:
            if event_type in self._listeners and handler in self._listeners[event_type]:
                self._listeners[event_type].remove(handler)

    def emit(self, event_type: str, event: Any) -> None:
        with self._lock:
            handlers = self._listeners.get(event_type, []).copy()
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Handler error: {e}")