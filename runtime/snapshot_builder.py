# runtime/snapshot_builder.py
from runtime.context import get_app_context

class SnapshotBuilder:
    def __init__(self):
        self.context = get_app_context()

    def build_snapshot(self):
        rc = self.context.get_runtime_controller()
        if not rc:
            return {}
        try:
            health = rc.get_health_score().get('data', {})
            runtime_health = health.get('score', 0)

            pm = rc._plugin_manager
            all_plugins = pm.get_plugins()
            active_plugins = sum(1 for v in all_plugins.values() if v)
            quarantined = sum(1 for name in pm.get_plugin_names() if pm.is_quarantined(name))

            executor = pm._executor_registry.get("subprocess") if hasattr(pm, '_executor_registry') else None
            running_processes = 0
            if executor and hasattr(executor, '_process_manager'):
                processes = executor._process_manager.get_all_processes()
                running_processes = len(processes)

            from dashboard import notification_manager
            alerts = 0
            if notification_manager:
                recent = notification_manager.get_history(limit=50)
                alerts = len([n for n in recent if n.get('type') in ('error', 'warning', 'critical')])

            last_backup_status = "NO BACKUP"
            last_backup_time = None
            try:
                from dashboard import state_manager
                if state_manager:
                    data = state_manager.storage.load()
                    if data and 'created_at' in data:
                        last_backup_time = data['created_at']
                        last_backup_status = "OK"
            except:
                pass

            plugins = []
            for name in pm.get_plugin_names():
                plugin = pm.get_plugin_object(name)
                if not plugin:
                    continue
                state = pm.get_plugin_state(name)
                health = pm.get_plugin_health_score(name)
                exec_mode = getattr(plugin, 'execution_mode', 'inprocess')
                plugins.append({
                    "name": name,
                    "version": plugin.PLUGIN_INFO.get('version', '0.0.0'),
                    "status": state.upper() if state else "UNKNOWN",
                    "health": health,
                    "execution_mode": exec_mode
                })

            return {
                "runtime_health": runtime_health,
                "active_plugins": active_plugins,
                "quarantined_plugins": quarantined,
                "running_processes": running_processes,
                "alerts": alerts,
                "last_backup": {
                    "status": last_backup_status,
                    "created_at": last_backup_time
                },
                "plugins": plugins
            }
        except Exception as e:
            return {"error": str(e)}

    def refresh_snapshot(self):
        snapshot = self.build_snapshot()
        self.context.update_snapshot(snapshot)
        return snapshot