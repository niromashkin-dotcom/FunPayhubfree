# runtime/observability/observability_hub.py
from eventbus import EventBus
from runtime.event_types import Event
from runtime.observability.event_store import EventStore
from runtime.observability.metrics import MetricsCollector
from runtime.observability.health_engine import HealthEngineV2

class ObservabilityHub:
    def __init__(self, event_bus: EventBus, max_events: int = 1000):
        self._event_bus = event_bus
        self._event_store = EventStore(max_events)
        self._metrics = MetricsCollector()
        self._health_engine = HealthEngineV2(self._metrics, self._event_store)

        self._event_bus.subscribe("plugin_action", self._on_event)
        self._last_health = None

    def _on_event(self, event: Event):
        self._event_store.add(event)
        self._metrics.record_event(event.plugin, event.severity.value)
        self._publish_metrics(event.plugin)
        self._publish_health()

    def _publish_metrics(self, plugin_name: str):
        metrics = self._metrics.get_plugin_metrics(plugin_name)
        if metrics:
            self._event_bus.emit("metrics_update", {"plugin": plugin_name, "metrics": metrics})

    def _publish_health(self):
        health = self._health_engine.get_detailed_health()
        # Отправляем только при изменении score или статуса
        current = (health["score"], health["status"])
        if self._last_health != current:
            self._last_health = current
            self._event_bus.emit("health_update", {"score": health["score"], "status": health["status"]})

    def record_plugin_state_change(self, plugin_name: str):
        self._metrics.record_state_change(plugin_name)

    def record_plugin_restart(self, plugin_name: str):
        self._metrics.record_restart(plugin_name)
        self._publish_metrics(plugin_name)

    def record_plugin_uptime_start(self, plugin_name: str):
        self._metrics.set_uptime_start(plugin_name)

    def get_health_score(self) -> int:
        return self._health_engine.calculate_score()

    def get_health_status(self) -> str:
        return self._health_engine.get_status()

    def get_detailed_health(self) -> dict:
        return self._health_engine.get_detailed_health()

    def get_plugin_metrics(self, plugin_name: str = None):
        if plugin_name:
            return self._metrics.get_plugin_metrics(plugin_name)
        return self._metrics.get_all_metrics()

    def get_event_history(self, limit: int = None) -> list:
        events = self._event_store.get_all()
        if limit:
            events = events[-limit:]
        return [e.to_dict() for e in events]

    def get_events_by_correlation(self, correlation_id: str) -> list:
        return [e.to_dict() for e in self._event_store.get_by_correlation(correlation_id)]

    def get_stats(self) -> dict:
        return self._event_store.get_stats()