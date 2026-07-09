# runtime/state/snapshot_engine.py
import time
from typing import Dict, Any

class SnapshotEngine:
    CURRENT_VERSION = 1

    def __init__(self, runtime_controller, observability_hub, notification_manager):
        self.runtime_controller = runtime_controller
        self.observability_hub = observability_hub
        self.notification_manager = notification_manager

    def create_snapshot(self) -> Dict[str, Any]:
        pm = self.runtime_controller._plugin_manager
        plugin_states = {}
        plugin_names = pm.get_plugin_names()
        for name in plugin_names:
            state = pm.get_plugin_state(name)
            plugin_states[name] = state

        metrics = self.observability_hub.get_plugin_metrics()
        health = self.observability_hub.get_detailed_health()
        notifications = self.notification_manager.get_history(limit=1000)
        quarantine_data = pm.get_quarantine_data()   # новая строка

        return {
            "version": self.CURRENT_VERSION,
            "created_at": time.time(),
            "data": {
                "plugin_states": plugin_states,
                "metrics": metrics,
                "health": health,
                "notifications": notifications,
                "quarantine": quarantine_data      # новая строка
            }
        }

    def apply_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        if not self._validate_snapshot(snapshot):
            print("[SnapshotEngine] Invalid snapshot, skip restore")
            return False

        data = snapshot.get("data", {})
        plugin_states = data.get("plugin_states", {})
        quarantine_data = data.get("quarantine", {})

        # Восстановление состояний плагинов
        self.runtime_controller._plugin_manager.restore_states(plugin_states)
        # Восстановление карантина
        if quarantine_data:
            self.runtime_controller._plugin_manager.restore_quarantine(quarantine_data)

        print(f"[SnapshotEngine] Applied snapshot from version {snapshot.get('version')}")
        return True

    def _validate_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        if not isinstance(snapshot, dict):
            return False
        if "version" not in snapshot:
            return False
        if "created_at" not in snapshot:
            return False
        if "data" not in snapshot or not isinstance(snapshot["data"], dict):
            return False
        return True