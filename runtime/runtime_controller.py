# runtime/runtime_controller.py
import time
import uuid
from typing import Dict, List, Optional, Any
from plugins.plugin_manager import PluginManager
from runtime.runtime_log import RuntimeLog, LogLevel
from eventbus import EventBus
from runtime.event_types import Event, EventAction, EventResult, EventSource, EventSeverity


class RuntimeController:
    def __init__(self, plugin_manager: PluginManager, runtime_log: RuntimeLog, event_bus: EventBus):
        self._plugin_manager = plugin_manager
        self._runtime_log = runtime_log
        self._event_bus = event_bus
        self._runtime_status = "running"
        self._observability = None  # будет установлен снаружи

        if self._event_bus:
            self._plugin_manager.set_event_bus(self._event_bus)

        self._runtime_log.info("RuntimeController", "Initialized")

    def set_observability_hub(self, hub):
        self._observability = hub

    def _emit_event(self, action: EventAction, plugin: str, result: EventResult,
                    state: str = None, message: str = None, correlation_id: str = None):
        if not self._event_bus:
            return
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        event = Event(
            action=action,
            plugin=plugin,
            result=result,
            state=state,
            source=EventSource.RUNTIME_CONTROLLER,
            message=message,
            correlation_id=correlation_id
        )
        self._event_bus.emit("plugin_action", event)
        return event

    def _log_operation(self, command: str, plugin: str, success: bool,
                       message: str = None, old_state: str = None, new_state: str = None):
        if success:
            log_msg = f"{command} | {plugin}"
            if old_state and new_state:
                log_msg += f" | {old_state} → {new_state}"
            if message:
                log_msg += f" | {message}"
            self._runtime_log.info("RuntimeController", log_msg)
        else:
            level = LogLevel.WARNING if message and ("not found" in message.lower() or "already" in message.lower()) else LogLevel.ERROR
            log_msg = f"{command} FAILED | {plugin}"
            if message:
                log_msg += f" | {message}"
            self._runtime_log.add(level, "RuntimeController", log_msg)

    def _get_health_status(self) -> str:
        if self._runtime_status != "running":
            return "ERROR"
        for name in self._plugin_manager.get_plugin_names():
            state = self._plugin_manager.get_plugin_state(name)
            if state == "error":
                return "DEGRADED"
        return "OK"

    def _get_plugins_list(self) -> List[dict]:
        plugins = []
        for name in self._plugin_manager.get_plugin_names():
            state = self._plugin_manager.get_plugin_state(name)
            plugin = self._plugin_manager.get_plugin_object(name)
            info = plugin.get_info() if plugin else {"name": name, "version": "unknown"}
            plugins.append({
                "module": name,
                "name": info.get("name", name),
                "version": info.get("version", "0.0.0"),
                "state": state or "unknown"
            })
        return plugins

    def _build_response(self, success: bool, command: str, plugin: str = None,
                        state: str = None, data: dict = None, message: str = None) -> dict:
        return {
            "success": success,
            "command": command,
            "plugin": plugin,
            "state": state,
            "data": data or {},
            "message": message or ("OK" if success else "Failed"),
            "timestamp": time.time()
        }

    def enable_plugin(self, name: str, correlation_id: str = None) -> dict:
        command = "enable_plugin"
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        if self._runtime_status != "running":
            resp = self._build_response(False, command, name, message=f"Runtime status: {self._runtime_status}")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.ENABLE, name, EventResult.FAILED, message=resp["message"], correlation_id=correlation_id)
            return resp
        if not self._plugin_manager.plugin_exists(name):
            resp = self._build_response(False, command, name, message="Plugin not found")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.ENABLE, name, EventResult.NOT_FOUND, message=resp["message"], correlation_id=correlation_id)
            return resp
        current_state = self._plugin_manager.get_plugin_state(name)
        if current_state == "active":
            resp = self._build_response(True, command, name, state="active", message="Plugin already active")
            self._log_operation(command, name, True, message=resp["message"], old_state=current_state, new_state=current_state)
            self._emit_event(EventAction.ENABLE, name, EventResult.ALREADY_ACTIVE, state="active", message=resp["message"], correlation_id=correlation_id)
            return resp
        if current_state not in ["loaded", "disabled"]:
            resp = self._build_response(False, command, name, state=current_state, message=f"Cannot enable from state: {current_state}")
            self._log_operation(command, name, False, message=resp["message"], old_state=current_state)
            self._emit_event(EventAction.ENABLE, name, EventResult.FAILED, state=current_state, message=resp["message"], correlation_id=correlation_id)
            return resp
        self._plugin_manager.enable(name)
        new_state = self._plugin_manager.get_plugin_state(name)
        if new_state != "active":
            resp = self._build_response(False, command, name, state=new_state, message="Enable failed")
            self._log_operation(command, name, False, message=resp["message"], old_state=current_state, new_state=new_state)
            self._emit_event(EventAction.ENABLE, name, EventResult.FAILED, state=new_state, message=resp["message"], correlation_id=correlation_id)
            return resp
        resp = self._build_response(True, command, name, state=new_state, message="Plugin enabled")
        self._log_operation(command, name, True, message=resp["message"], old_state=current_state, new_state=new_state)
        self._emit_event(EventAction.ENABLE, name, EventResult.SUCCESS, state="active", message=resp["message"], correlation_id=correlation_id)
        if self._observability:
            self._observability.record_plugin_uptime_start(name)
        return resp

    def disable_plugin(self, name: str, correlation_id: str = None) -> dict:
        command = "disable_plugin"
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        if self._runtime_status != "running":
            resp = self._build_response(False, command, name, message=f"Runtime status: {self._runtime_status}")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.DISABLE, name, EventResult.FAILED, message=resp["message"], correlation_id=correlation_id)
            return resp
        if not self._plugin_manager.plugin_exists(name):
            resp = self._build_response(False, command, name, message="Plugin not found")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.DISABLE, name, EventResult.NOT_FOUND, message=resp["message"], correlation_id=correlation_id)
            return resp
        current_state = self._plugin_manager.get_plugin_state(name)
        if current_state != "active":
            resp = self._build_response(False, command, name, state=current_state, message="Plugin not active")
            self._log_operation(command, name, False, message=resp["message"], old_state=current_state)
            self._emit_event(EventAction.DISABLE, name, EventResult.FAILED, state=current_state, message=resp["message"], correlation_id=correlation_id)
            return resp
        self._plugin_manager.disable(name)
        new_state = self._plugin_manager.get_plugin_state(name)
        if new_state != "disabled":
            resp = self._build_response(False, command, name, state=new_state, message="Disable failed")
            self._log_operation(command, name, False, message=resp["message"], old_state=current_state, new_state=new_state)
            self._emit_event(EventAction.DISABLE, name, EventResult.FAILED, state=new_state, message=resp["message"], correlation_id=correlation_id)
            return resp
        resp = self._build_response(True, command, name, state=new_state, message="Plugin disabled")
        self._log_operation(command, name, True, message=resp["message"], old_state=current_state, new_state=new_state)
        self._emit_event(EventAction.DISABLE, name, EventResult.SUCCESS, state="disabled", message=resp["message"], correlation_id=correlation_id)
        return resp

    def restart_plugin(self, name: str, correlation_id: str = None) -> dict:
        command = "restart_plugin"
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        if self._runtime_status != "running":
            resp = self._build_response(False, command, name, message=f"Runtime status: {self._runtime_status}")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.RESTART, name, EventResult.FAILED, message=resp["message"], correlation_id=correlation_id)
            return resp
        if not self._plugin_manager.plugin_exists(name):
            resp = self._build_response(False, command, name, message="Plugin not found")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.RESTART, name, EventResult.NOT_FOUND, message=resp["message"], correlation_id=correlation_id)
            return resp
        current_state = self._plugin_manager.get_plugin_state(name)
        if current_state not in ["active", "disabled", "loaded"]:
            resp = self._build_response(False, command, name, state=current_state, message=f"Cannot restart from state: {current_state}")
            self._log_operation(command, name, False, message=resp["message"], old_state=current_state)
            self._emit_event(EventAction.RESTART, name, EventResult.FAILED, state=current_state, message=resp["message"], correlation_id=correlation_id)
            return resp
        if current_state == "active":
            self._plugin_manager.disable(name)
            after_disable = self._plugin_manager.get_plugin_state(name)
            if after_disable not in ["disabled", "loaded"]:
                resp = self._build_response(False, command, name, state=after_disable, message="Restart failed at disable step")
                self._log_operation(command, name, False, message=resp["message"], old_state=current_state, new_state=after_disable)
                self._emit_event(EventAction.RESTART, name, EventResult.FAILED, state=after_disable, message=resp["message"], correlation_id=correlation_id)
                return resp
        self._plugin_manager.enable(name)
        new_state = self._plugin_manager.get_plugin_state(name)
        if new_state != "active":
            resp = self._build_response(False, command, name, state=new_state, message="Restart failed at enable step")
            self._log_operation(command, name, False, message=resp["message"], old_state=current_state, new_state=new_state)
            self._emit_event(EventAction.RESTART, name, EventResult.FAILED, state=new_state, message=resp["message"], correlation_id=correlation_id)
            return resp
        resp = self._build_response(True, command, name, state=new_state, message="Plugin restarted")
        self._log_operation(command, name, True, message=resp["message"], old_state=current_state, new_state=new_state)
        self._emit_event(EventAction.RESTART, name, EventResult.SUCCESS, state="active", message=resp["message"], correlation_id=correlation_id)
        if self._observability:
            self._observability.record_plugin_restart(name)
        return resp

    def reload_plugin_config(self, name: str, correlation_id: str = None) -> dict:
        command = "reload_plugin_config"
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        if self._runtime_status != "running":
            resp = self._build_response(False, command, name, message=f"Runtime status: {self._runtime_status}")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.RELOAD_CONFIG, name, EventResult.FAILED, message=resp["message"], correlation_id=correlation_id)
            return resp
        if not self._plugin_manager.plugin_exists(name):
            resp = self._build_response(False, command, name, message="Plugin not found")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.RELOAD_CONFIG, name, EventResult.NOT_FOUND, message=resp["message"], correlation_id=correlation_id)
            return resp
        plugin = self._plugin_manager.get_plugin_object(name)
        if not plugin:
            resp = self._build_response(False, command, name, message="Plugin not loaded")
            self._log_operation(command, name, False, message=resp["message"])
            self._emit_event(EventAction.RELOAD_CONFIG, name, EventResult.FAILED, message=resp["message"], correlation_id=correlation_id)
            return resp
        old_config = plugin.get_config()
        plugin.reload_config()
        new_config = plugin.get_config()
        resp = self._build_response(True, command, name, data={"old_config": old_config, "new_config": new_config}, message="Config reloaded")
        self._log_operation(command, name, True, message=resp["message"])
        self._emit_event(EventAction.RELOAD_CONFIG, name, EventResult.SUCCESS, message=resp["message"], correlation_id=correlation_id)
        return resp

    # Остальные методы (list_plugins, get_plugin_info, get_plugin_state, get_all_states, get_plugins,
    # get_runtime_status, get_runtime_info, get_runtime_health, get_system_snapshot, shutdown_runtime,
    # get_runtime_logs, get_runtime_logs_count, clear_runtime_logs) остаются без изменений (как в прошлой версии).
    # Для краткости я их опускаю, но они должны быть скопированы из предыдущей стабильной версии.
    # Ниже — заглушки, но ты должен вставить полные методы из предыдущего runtime_controller.py.

    def list_plugins(self) -> dict:
        command = "list_plugins"
        plugins = self._get_plugins_list()
        return self._build_response(True, command, data={"plugins": plugins}, message="Plugins listed")

    def get_plugin_info(self, name: str) -> dict:
        command = "get_plugin_info"
        if not self._plugin_manager.plugin_exists(name):
            return self._build_response(False, command, name, message="Plugin not found")
        state = self._plugin_manager.get_plugin_state(name)
        plugin = self._plugin_manager.get_plugin_object(name)
        if plugin:
            info = plugin.get_info()
            return self._build_response(True, command, name, state=state or "unknown", data={
                "module": name,
                "name": info.get("name", name),
                "version": info.get("version", "0.0.0"),
                "author": info.get("author", "Unknown"),
                "description": info.get("description", ""),
                "config": plugin.get_config()
            }, message="Plugin info retrieved")
        else:
            return self._build_response(True, command, name, state=state or "unknown", data={
                "module": name,
                "name": name,
                "version": "unknown",
                "config": {}
            }, message="Plugin info retrieved (not fully loaded)")

    def get_plugin_state(self, name: str) -> dict:
        command = "get_plugin_state"
        if not self._plugin_manager.plugin_exists(name):
            return self._build_response(False, command, name, message="Plugin not found")
        state = self._plugin_manager.get_plugin_state(name)
        return self._build_response(True, command, name, state=state or "unknown", message="Plugin state retrieved")

    def get_all_states(self) -> dict:
        command = "get_all_states"
        states = {}
        for name in self._plugin_manager.get_plugin_names():
            states[name] = self._plugin_manager.get_plugin_state(name) or "unknown"
        return self._build_response(True, command, data={"states": states}, message="All states retrieved")

    def get_plugins(self) -> dict:
        command = "get_plugins"
        plugins = {}
        for name in self._plugin_manager.get_plugin_names():
            state = self._plugin_manager.get_plugin_state(name)
            plugins[name] = (state == "active")
        return self._build_response(True, command, data={"plugins": plugins}, message="Plugins status retrieved")

    def get_runtime_status(self) -> dict:
        command = "get_runtime_status"
        return self._build_response(True, command, data={"status": self._runtime_status}, message="Runtime status retrieved")

    def get_runtime_info(self) -> dict:
        command = "get_runtime_info"
        return self._build_response(True, command, data={
            "status": self._runtime_status,
            "health": self._get_health_status(),
            "plugins_count": len(self._plugin_manager.get_plugin_names()),
            "plugins": self._get_plugins_list()
        }, message="Runtime info retrieved")

    def get_runtime_health(self) -> dict:
        command = "get_runtime_health"
        health = self._get_health_status()
        return self._build_response(True, command, data={"health": health}, message="Health status retrieved")

    def get_system_snapshot(self) -> dict:
        command = "get_system_snapshot"
        snapshot = {
            "runtime_status": self._runtime_status,
            "health": self._get_health_status(),
            "plugins_count": len(self._plugin_manager.get_plugin_names()),
            "plugins": self._get_plugins_list(),
            "logs_stats": {
                "total_entries": self._runtime_log.count(),
                "max_entries": self._runtime_log.MAX_LOG_ENTRIES
            }
        }
        return self._build_response(True, command, data=snapshot, message="System snapshot retrieved")

    def shutdown_runtime(self) -> dict:
        command = "shutdown_runtime"
        self._runtime_log.info("Runtime", "Shutdown initiated")
        self._runtime_status = "stopping"
        self._emit_event(EventAction.SHUTDOWN, "runtime", EventResult.SUCCESS, message="Shutdown initiated")
        self._runtime_status = "stopped"
        self._runtime_log.info("Runtime", "Shutdown complete")
        self._emit_event(EventAction.SHUTDOWN, "runtime", EventResult.SUCCESS, message="Shutdown complete")
        return self._build_response(True, command, message="Runtime shutdown initiated")

    def get_runtime_logs(self, limit: int = None, level: str = None) -> dict:
        command = "get_runtime_logs"
        log_level = None
        if level:
            try:
                log_level = LogLevel(level.upper())
            except ValueError:
                pass
        entries = self._runtime_log.get_entries(limit=limit, level=log_level)
        return self._build_response(True, command, data={
            "logs": entries,
            "count": len(entries),
            "limit": limit,
            "level": level
        }, message="Logs retrieved")

    def get_runtime_logs_count(self) -> dict:
        command = "get_runtime_logs_count"
        return self._build_response(True, command, data={"count": self._runtime_log.count()}, message="Log count retrieved")

    def clear_runtime_logs(self) -> dict:
        command = "clear_runtime_logs"
        self._runtime_log.clear()
        self._emit_event(EventAction.CLEAR_LOGS, "runtime", EventResult.SUCCESS, message="Runtime logs cleared")
        return self._build_response(True, command, message="Runtime logs cleared")

    # Observability API
    def get_health_score(self) -> dict:
        command = "get_health_score"
        if self._observability:
            score = self._observability.get_health_score()
            status = self._observability.get_health_status()
            return self._build_response(True, command, data={"score": score, "status": status}, message="Health score retrieved")
        return self._build_response(False, command, message="Observability not available")

    def get_detailed_health(self) -> dict:
        command = "get_detailed_health"
        if self._observability:
            return self._build_response(True, command, data=self._observability.get_detailed_health(), message="Detailed health retrieved")
        return self._build_response(False, command, message="Observability not available")

    def get_plugin_metrics(self, plugin_name: str = None) -> dict:
        command = "get_plugin_metrics"
        if self._observability:
            metrics = self._observability.get_plugin_metrics(plugin_name)
            return self._build_response(True, command, data=metrics, message="Plugin metrics retrieved")
        return self._build_response(False, command, message="Observability not available")

    def get_event_history(self, limit: int = None) -> dict:
        command = "get_event_history"
        if self._observability:
            events = self._observability.get_event_history(limit)
            return self._build_response(True, command, data={"events": events, "count": len(events)}, message="Event history retrieved")
        return self._build_response(False, command, message="Observability not available")

    def get_correlation_events(self, correlation_id: str) -> dict:
        command = "get_correlation_events"
        if self._observability:
            events = self._observability.get_events_by_correlation(correlation_id)
            return self._build_response(True, command, data={"events": events, "count": len(events)}, message="Correlation events retrieved")
        return self._build_response(False, command, message="Observability not available")

    def get_observability_stats(self) -> dict:
        command = "get_observability_stats"
        if self._observability:
            stats = self._observability.get_stats()
            return self._build_response(True, command, data=stats, message="Observability stats retrieved")
        return self._build_response(False, command, message="Observability not available")