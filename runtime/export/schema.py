# runtime/export/schema.py
import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from runtime.export.models import ExportData


def get_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["format_version", "runtime_version", "export_type", "created_at", "data"],
        "properties": {
            "format_version": {"type": "integer", "minimum": 1},
            "runtime_version": {"type": "string"},
            "export_type": {"type": "string", "enum": ["configuration", "backup", "migration"]},
            "created_at": {"type": "string"},
            "data": {"type": "object"}
        }
    }


def validate_export(data: Dict[str, Any]) -> Tuple[bool, str, Optional[ExportData]]:
    """Проверяет структуру импортируемого JSON и возвращает объект ExportData."""
    # 1. Проверка основных полей
    if "format_version" not in data:
        return False, "Missing format_version", None
    if data["format_version"] != 1:
        return False, f"Unsupported format_version: {data['format_version']}", None

    if "export_type" not in data:
        return False, "Missing export_type", None
    if data["export_type"] != "configuration":
        return False, f"Unsupported export_type: {data['export_type']} (only 'configuration' allowed)", None

    if "runtime_version" not in data:
        return False, "Missing runtime_version", None

    if "data" not in data:
        return False, "Missing data", None

    # 2. Парсим data
    export_data = ExportData(
        format_version=data["format_version"],
        runtime_version=data["runtime_version"],
        export_type=data["export_type"],
        created_at=data.get("created_at", datetime.utcnow().isoformat())
    )

    # 3. Плагины
    plugins_data = data["data"].get("plugins", [])
    for p in plugins_data:
        from runtime.export.models import PluginExport
        export_data.plugins.append(PluginExport(
            module=p.get("module"),
            name=p.get("name"),
            version=p.get("version"),
            enabled=p.get("enabled", True),
            config=p.get("config", {}),
            dependencies=p.get("dependencies", []),
            optional_dependencies=p.get("optional_dependencies", [])
        ))

    # 4. runtime_settings
    rs = data["data"].get("runtime_settings", {})
    export_data.runtime_settings.health_thresholds = rs.get("health_thresholds", export_data.runtime_settings.health_thresholds)
    export_data.runtime_settings.quarantine_policy = rs.get("quarantine_policy", export_data.runtime_settings.quarantine_policy)
    export_data.runtime_settings.watchdog_interval = rs.get("watchdog_interval", export_data.runtime_settings.watchdog_interval)
    export_data.runtime_settings.autosave_interval = rs.get("autosave_interval", export_data.runtime_settings.autosave_interval)

    # 5. observability
    obs = data["data"].get("observability", {})
    export_data.observability.metrics_retention = obs.get("metrics_retention", export_data.observability.metrics_retention)
    export_data.observability.health_score_enabled = obs.get("health_score_enabled", export_data.observability.health_score_enabled)
    export_data.observability.event_store_max = obs.get("event_store_max", export_data.observability.event_store_max)

    # 6. notifications
    notif = data["data"].get("notifications", {})
    export_data.notifications.enabled = notif.get("enabled", export_data.notifications.enabled)
    export_data.notifications.discord_webhook = notif.get("discord_webhook", export_data.notifications.discord_webhook)
    export_data.notifications.log_enabled = notif.get("log_enabled", export_data.notifications.log_enabled)
    export_data.notifications.dashboard_enabled = notif.get("dashboard_enabled", export_data.notifications.dashboard_enabled)
    export_data.notifications.rate_limit_per_minute = notif.get("rate_limit_per_minute", export_data.notifications.rate_limit_per_minute)

    return True, "Valid", export_data