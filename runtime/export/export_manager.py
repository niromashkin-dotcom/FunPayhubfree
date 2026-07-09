# runtime/export/export_manager.py
import json
from typing import Dict, Any
from runtime.export.models import ExportData, PluginExport
from runtime.export.schema import get_schema


class ExportManager:
    def __init__(self, runtime_controller, config):
        self.runtime_controller = runtime_controller
        self.config = config
        self.pm = runtime_controller._plugin_manager

    def create_export(self) -> ExportData:
        export = ExportData()

        for name in self.pm.get_plugin_names():
            plugin = self.pm.get_plugin_object(name)
            if plugin:
                export.plugins.append(PluginExport(
                    module=name,
                    name=plugin.PLUGIN_INFO.get("name", name),
                    version=plugin.PLUGIN_INFO.get("version", "0.0.0"),
                    enabled=plugin.is_enabled(),
                    config=plugin.get_config(),
                    dependencies=plugin.get_dependencies(),
                    optional_dependencies=plugin.get_optional_dependencies()
                ))

        export.runtime_settings = self._get_runtime_settings()
        export.observability = self._get_observability_settings()
        export.notifications = self._get_notifications_settings()
        return export

    def _get_runtime_settings(self):
        from runtime.export.models import RuntimeSettingsExport
        pm = self.pm
        return RuntimeSettingsExport(
            health_thresholds={
                "normal": getattr(pm, 'health_threshold_normal', 80),
                "quarantine": getattr(pm, 'quarantine_threshold', 40),
                "checks_required": getattr(pm, 'quarantine_checks_required', 3)
            },
            quarantine_policy={"backoff_seconds": [60, 120, 300]},
            watchdog_interval=getattr(pm, '_watchdog_interval', 10),
            autosave_interval=60
        )

    def _get_observability_settings(self):
        from runtime.export.models import ObservabilityExport
        return ObservabilityExport(
            metrics_retention=1000,
            health_score_enabled=True,
            event_store_max=1000
        )

    def _get_notifications_settings(self):
        from runtime.export.models import NotificationsExport
        return NotificationsExport(
            enabled=True,
            discord_webhook=self.config.get("discord_webhook"),
            log_enabled=True,
            dashboard_enabled=True,
            rate_limit_per_minute=10
        )

    def export_to_json(self, pretty: bool = True) -> str:
        export = self.create_export()
        data = {
            "format_version": export.format_version,
            "runtime_version": export.runtime_version,
            "export_type": export.export_type,
            "created_at": export.created_at,
            "data": {
                "plugins": [p.__dict__ for p in export.plugins],
                "runtime_settings": export.runtime_settings.__dict__,
                "observability": export.observability.__dict__,
                "notifications": export.notifications.__dict__
            }
        }
        return json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)