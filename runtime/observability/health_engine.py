# runtime/observability/health_engine.py
from runtime.observability.metrics import MetricsCollector
from runtime.observability.event_store import EventStore


class HealthEngineV2:
    def __init__(self, metrics: MetricsCollector, event_store: EventStore):
        self._metrics = metrics
        self._event_store = event_store

    def calculate_score(self) -> int:
        score = 100
        stats = self._event_store.get_stats()
        # Не более 30 штрафа за ошибки
        score -= min(30, stats["errors"] * 5)
        # Штраф за рестарты
        total_restarts = sum(m.get("restarts", 0) for m in self._metrics.get_all_metrics().values())
        score -= min(20, total_restarts * 2)
        # Стабильность плагинов
        avg_stability = self._metrics.get_summary()["average_stability"]
        if avg_stability < 70:
            score -= (70 - avg_stability) // 2
        return max(0, min(100, int(score)))

    def get_status(self) -> str:
        score = self.calculate_score()
        if score >= 95:
            return "EXCELLENT"
        if score >= 80:
            return "GOOD"
        if score >= 60:
            return "STABLE"
        if score >= 40:
            return "DEGRADED"
        return "CRITICAL"

    def get_detailed_health(self) -> dict:
        return {
            "score": self.calculate_score(),
            "status": self.get_status(),
            "metrics_summary": self._metrics.get_summary(),
            "event_stats": self._event_store.get_stats()
        }