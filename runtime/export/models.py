# runtime/export/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class PluginExport:
    module: str
    name: str
    version: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)


@dataclass
class RuntimeSettingsExport:
    health_thresholds: Dict[str, int] = field(default_factory=lambda: {
        "normal": 80,
        "quarantine": 40,
        "checks_required": 3
    })
    quarantine_policy: Dict[str, List[int]] = field(default_factory=lambda: {
        "backoff_seconds": [60, 120, 300]
    })
    watchdog_interval: int = 10
    autosave_interval: int = 60


@dataclass
class ObservabilityExport:
    metrics_retention: int = 1000
    health_score_enabled: bool = True
    event_store_max: int = 1000


@dataclass
class NotificationsExport:
    enabled: bool = True
    discord_webhook: Optional[str] = None
    log_enabled: bool = True
    dashboard_enabled: bool = True
    rate_limit_per_minute: int = 10


@dataclass
class ExportData:
    format_version: int = 1
    runtime_version: str = "0.1.0"
    export_type: str = "configuration"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    plugins: List[PluginExport] = field(default_factory=list)
    runtime_settings: RuntimeSettingsExport = field(default_factory=RuntimeSettingsExport)
    observability: ObservabilityExport = field(default_factory=ObservabilityExport)
    notifications: NotificationsExport = field(default_factory=NotificationsExport)