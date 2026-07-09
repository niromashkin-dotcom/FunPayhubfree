# runtime/__init__.py
#
# ВАЖНО: до 08.07.2026 здесь был `from runtime.runtime import RuntimeOrchestrator, run_system`.
# runtime/runtime.py — часть legacy-кластера (Cardinal/dashboard), никогда не подключённого к
# живой точке входа (hub_bootstrap.py сам говорит: "Initializes plugin system WITHOUT
# Cardinal/RuntimeOrchestrator/dashboard"), и файл перенесён в _archive/legacy_cluster_dead_code/.
# Раз ЛЮБОЙ импорт `runtime.<что угодно>` в Python сначала выполняет этот __init__.py — оставленная
# строка импорта уронила бы АБСОЛЮТНО ВЕСЬ пакет runtime (а значит seller_service.py и всё
# остальное) сразу после удаления файла. Убрано сознательно вместе с переносом файла.
from runtime.runtime_log import RuntimeLog, LogLevel
from runtime.runtime_controller import RuntimeController
from runtime.event_types import Event, EventAction, EventResult, EventSource, EventSeverity
from runtime.observability.observability_hub import ObservabilityHub
from runtime.observability.event_store import EventStore
from runtime.observability.metrics import MetricsCollector, PluginMetrics
from runtime.observability.health_engine import HealthEngineV2
from runtime.websocket.websocket_hub import WebSocketHub
from runtime.ai_team_orchestrator import AITeamOrchestrator, LogMonitor, TaskManager
from runtime.ai_team.ai_team_orchestrator import AITeamOrchestrator as AITeamOrchestratorV2
from runtime.ai_team.model_manager import AIModelManager
from runtime.ai_team.scheduled_tasks import ScheduledTasks

__all__ = [
    'RuntimeLog', 'LogLevel',
    'RuntimeController',
    'Event', 'EventAction', 'EventResult', 'EventSource', 'EventSeverity',
    'ObservabilityHub', 'EventStore', 'MetricsCollector', 'PluginMetrics', 'HealthEngineV2',
    'WebSocketHub',
    'AITeamOrchestrator', 'LogMonitor', 'TaskManager', 'AITeamOrchestratorV2', 'AIModelManager', 'ScheduledTasks'
]