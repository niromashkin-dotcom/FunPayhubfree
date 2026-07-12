# plugins/plugin_manager.py (обновлён для поддержки execution_mode)
import threading
import time
from typing import Dict, Type, List, Optional
from collections import deque

from plugins.plugin_base import PluginBase
from plugins.plugin_state import PluginState, PluginStateMachine, PluginErrorContext
from plugins.plugin_registry import PluginRegistry
from plugins.dependency_manager import DependencyGraph, MissingDependencyError, CircularDependencyError
from plugins.health_score import PluginHealthScore
from plugins.execution import get_executor_registry

class PluginManager:
    def __init__(self, state_api, event_bus=None):
        self.state_api = state_api
        self.event_bus = event_bus
        self.plugins: Dict[str, PluginBase] = {}
        self._fsm: Dict[str, PluginStateMachine] = {}
        self.registry = PluginRegistry()
        self.dep_graph = DependencyGraph()
        self._load_order: List[str] = []
        self._registration_complete = False
        self._health_scores: Dict[str, PluginHealthScore] = {}
        self._quarantine_map: Dict[str, Dict] = {}
        self._quarantine_attempts: Dict[str, int] = {}
        self._low_score_counter: Dict[str, int] = {}
        self._watchdog_interval = 10
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop_watchdog = threading.Event()
        self.health_threshold_normal = 80
        self.quarantine_threshold = 40
        self.quarantine_checks_required = 3
        self._executor_registry = get_executor_registry()

    def set_event_bus(self, event_bus):
        self.event_bus = event_bus

    def _get_fsm(self, module_name: str) -> Optional[PluginStateMachine]:
        return self._fsm.get(module_name)

    def _transition(self, module_name: str, target_state: PluginState, error: Exception = None) -> bool:
        fsm = self._get_fsm(module_name)
        if not fsm:
            return False
        if not fsm.can_transition(target_state):
            print(f"[PluginManager] {module_name}: cannot transition from {fsm.get_state_name()} to {target_state.value}")
            return False
        error_context = None
        if target_state == PluginState.ERROR and error:
            error_context = PluginErrorContext(
                message=f"Error in plugin {module_name}",
                original_exception=error
            )
        if not fsm.apply_transition(target_state, error_context):
            return False
        error_msg = error_context.to_string() if error_context else None
        self.registry.update_state(module_name, target_state.value, error_msg)
        plugin = self.plugins.get(module_name)
        if not plugin:
            return True
        try:
            if target_state == PluginState.LOADED:
                plugin._set_loaded(True)
                plugin.on_load()
            elif target_state == PluginState.ACTIVE:
                plugin._set_enabled(True)
                plugin.on_enable()
            elif target_state == PluginState.DISABLED:
                plugin._set_enabled(False)
                plugin.on_disable()
            elif target_state == PluginState.UNLOADED:
                plugin._set_loaded(False)
                plugin.on_unload()
            elif target_state == PluginState.ERROR and error:
                plugin.on_error(error)
        except Exception as e:
            print(f"[PluginManager] Error in hook {target_state.value} for {module_name}: {e}")
            self._transition(module_name, PluginState.ERROR, e)
            return False
        return True

    def register(self, module_name: str, plugin_cls: Type[PluginBase]):
        if module_name in self.plugins:
            print(f"[PluginManager] Plugin {module_name} already registered")
            return
        self.registry.register_metadata(module_name, plugin_cls.PLUGIN_INFO)
        deps = plugin_cls.get_dependencies(plugin_cls) if hasattr(plugin_cls, 'get_dependencies') else []
        opt_deps = plugin_cls.get_optional_dependencies(plugin_cls) if hasattr(plugin_cls, 'get_optional_dependencies') else []
        self.dep_graph.add_plugin(module_name, deps, opt_deps)
        fsm = PluginStateMachine(module_name)
        plugin = plugin_cls(module_name, self.state_api, self.event_bus)
        # B31: auto-subscribe plugins with on_event() to event_bus
        if self.event_bus and hasattr(plugin, 'on_event') and callable(getattr(plugin, 'on_event', None)):
            try:
                _priority = 100 if module_name == 'autosmm_plugin' else 0
                for _evt in ('new_order', 'new_message', 'review_received', 'order_completed', 'order_paid'):
                    self.event_bus.subscribe(_evt, plugin.on_event, priority=_priority)
                print('[PluginManager] ' + module_name + ' subscribed to event_bus: new_order/new_message/review_received (priority=' + str(_priority) + ')')
            except Exception as _e_sub:
                print('[PluginManager] subscribe failed for ' + module_name + ': ' + str(_e_sub))
        self.plugins[module_name] = plugin
        self._fsm[module_name] = fsm
        self._health_scores[module_name] = PluginHealthScore(module_name)
        print(f"[PluginManager] Plugin {module_name} registered (deps: {deps}, opt: {opt_deps})")

    def finalize_registration(self):
        available = set(self.plugins.keys())
        try:
            self.dep_graph.validate_dependencies(available)
        except MissingDependencyError as e:
            print(f"[PluginManager] Dependency validation failed: {e}")
            for plugin in self.plugins:
                if any(dep not in available for dep in self.dep_graph.graph.get(plugin, [])):
                    self._transition(plugin, PluginState.ERROR, Exception(str(e)))
            return
        try:
            self._load_order = self.dep_graph.topological_sort()
            print(f"[PluginManager] Load order: {self._load_order}")
        except CircularDependencyError as e:
            print(f"[PluginManager] Circular dependency error: {e}")
            for plugin in self.plugins:
                self._transition(plugin, PluginState.ERROR, e)
            return
        for name in self._load_order:
            self._transition(name, PluginState.LOADED)
            plugin = self.plugins[name]
            default_config = plugin.PLUGIN_INFO.get("default_config", {})
            plugin.load_config(default_config)
            info = plugin.get_info()
            print(f"[PluginManager] Plugin {name} loaded")
            print(f"  📦 {info.get('name')} v{info.get('version')} by {info.get('author')}")
        for name in self._load_order:
            self.enable(name)
        self._registration_complete = True
        self._start_watchdog()

    def _start_watchdog(self):
        if self._watchdog_thread is None or not self._watchdog_thread.is_alive():
            self._stop_watchdog.clear()
            self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
            self._watchdog_thread.start()
            print("[PluginManager] Watchdog started")

    def _watchdog_loop(self):
        while not self._stop_watchdog.wait(self._watchdog_interval):
            self._check_plugin_health()

    def _check_plugin_health(self):
        now = time.time()
        for name, fsm in self._fsm.items():
            if fsm.get_state() != PluginState.ACTIVE:
                continue
            hs = self._health_scores.get(name)
            if not hs:
                continue
            score = hs.calculate_score()
            if self.event_bus:
                from runtime.event_types import Event
                ev = Event(
                    action="health_update",
                    plugin=name,
                    result="score",
                    state=str(score),
                    source="plugin_manager",
                    message=f"Health score {score}"
                )
                self.event_bus.emit("plugin_health_score", {"plugin": name, "score": score})
            if score < self.quarantine_threshold:
                self._low_score_counter[name] = self._low_score_counter.get(name, 0) + 1
                if self._low_score_counter[name] >= self.quarantine_checks_required:
                    self.quarantine_plugin(name, f"Health score {score} below threshold {self.quarantine_threshold}")
            else:
                self._low_score_counter[name] = 0

    def quarantine_plugin(self, name: str, reason: str):
        if name in self._quarantine_map:
            return
        attempts = self._quarantine_attempts.get(name, 0) + 1
        self._quarantine_attempts[name] = attempts
        if attempts == 1:
            duration = 60
        elif attempts == 2:
            duration = 120
        elif attempts == 3:
            duration = 300
        else:
            duration = 86400
        quarantine_until = time.time() + duration
        self._quarantine_map[name] = {
            "until": quarantine_until,
            "level": attempts,
            "reason": reason,
            "score": self.get_plugin_health_score(name)
        }
        if self._get_fsm(name).get_state() == PluginState.ACTIVE:
            self.disable(name)
        print(f"[PluginManager] Plugin {name} quarantined until {quarantine_until} reason: {reason}")
        if self.event_bus:
            from runtime.event_types import Event, EventAction, EventResult, EventSource
            ev = Event(
                action=EventAction.DISABLE,
                plugin=name,
                result=EventResult.FAILED,
                state="quarantined",
                source=EventSource.PLUGIN_MANAGER,
                message=reason
            )
            self.event_bus.emit("plugin_action", ev)

    def release_quarantine(self, name: str):
        if name in self._quarantine_map:
            del self._quarantine_map[name]
            fsm = self._get_fsm(name)
            if fsm and fsm.get_state() == PluginState.DISABLED:
                self.enable(name)
            print(f"[PluginManager] Plugin {name} released from quarantine")

    def is_quarantined(self, name: str) -> bool:
        if name not in self._quarantine_map:
            return False
        if self._quarantine_map[name]["until"] < time.time():
            self.release_quarantine(name)
            return False
        return True

    def get_plugin_health_score(self, name: str) -> int:
        hs = self._health_scores.get(name)
        return hs.calculate_score() if hs else 100

    def get_all_health_scores(self) -> Dict[str, int]:
        return {name: hs.calculate_score() for name, hs in self._health_scores.items()}

    def get_quarantine_data(self) -> Dict[str, Dict]:
        return {name: data for name, data in self._quarantine_map.items()}

    def restore_quarantine(self, quarantine_data: Dict[str, Dict]):
        now = time.time()
        for name, data in quarantine_data.items():
            if data.get("until", 0) > now:
                self._quarantine_map[name] = data
                if self.plugin_exists(name):
                    fsm = self._get_fsm(name)
                    if fsm and fsm.get_state() == PluginState.ACTIVE:
                        self.disable(name)
                level = data.get("level", 0)
                if level > 0:
                    self._quarantine_attempts[name] = level
                print(f"[PluginManager] Restored quarantine for {name} until {data['until']}")

    def get_load_order(self) -> List[str]:
        return self._load_order

    def can_disable(self, module_name: str) -> bool:
        active = {name for name, fsm in self._fsm.items() if fsm.get_state() == PluginState.ACTIVE}
        can, blockers = self.dep_graph.can_disable(module_name, active)
        if blockers:
            print(f"[PluginManager] Cannot disable {module_name}, active hard dependents: {blockers}")
        return can

    def get_dependents(self, module_name: str) -> dict:
        hard, soft = self.dep_graph.get_dependents(module_name)
        return {"hard": list(hard), "soft": list(soft)}

    def unregister(self, module_name: str):
        if module_name not in self.plugins:
            return
        self._transition(module_name, PluginState.UNLOADED)
        del self.plugins[module_name]
        del self._fsm[module_name]
        self.dep_graph.remove_plugin(module_name)
        self._health_scores.pop(module_name, None)
        self._quarantine_map.pop(module_name, None)
        self._quarantine_attempts.pop(module_name, None)
        print(f"[PluginManager] Plugin {module_name} unloaded")

    def enable(self, module_name: str):
        if module_name not in self.plugins:
            return
        if self.is_quarantined(module_name):
            print(f"[PluginManager] Cannot enable {module_name} – quarantined")
            return
        fsm = self._get_fsm(module_name)
        if not fsm:
            return
        current = fsm.get_state()
        if current == PluginState.ACTIVE:
            return
        if current == PluginState.LOADED or current == PluginState.DISABLED:
            self._transition(module_name, PluginState.ACTIVE)
        else:
            print(f"[PluginManager] Cannot enable {module_name} from state {current.value}")

    def disable(self, module_name: str):
        if module_name not in self.plugins:
            return
        if not self.can_disable(module_name):
            print(f"[PluginManager] Cannot disable {module_name} due to hard dependents")
            return
        fsm = self._get_fsm(module_name)
        if fsm and fsm.get_state() == PluginState.ACTIVE:
            self._transition(module_name, PluginState.DISABLED)

    def emit(self, event_name: str, data=None):
        for module_name, plugin in self.plugins.items():
            if self.is_quarantined(module_name):
                continue
            fsm = self._fsm.get(module_name)
            if fsm and fsm.get_state() == PluginState.ACTIVE:
                # Выбираем executor на основе execution_mode плагина
                executor_name = getattr(plugin, "execution_mode", "inprocess")
                executor = self._executor_registry.get(executor_name)
                if executor is None:
                    executor = self._executor_registry.get_default()
                start = time.time()
                try:
                    executor.execute_event(plugin, event_name, data)
                except Exception as e:
                    print(f"[PluginManager] Error in plugin {module_name}: {e}")
                    self._transition(module_name, PluginState.ERROR, e)
                else:
                    duration = time.time() - start
                    hs = self._health_scores.get(module_name)
                    if hs:
                        hs.update_latency(duration)
                        hs.update_event_count(1)

    def get_plugin_state(self, module_name: str) -> Optional[str]:
        fsm = self._fsm.get(module_name)
        return fsm.get_state_name() if fsm else None

    def get_all_states(self) -> Dict[str, str]:
        return {name: fsm.get_state_name() for name, fsm in self._fsm.items()}

    def get_plugins(self) -> Dict[str, bool]:
        return {name: fsm.get_state() == PluginState.ACTIVE for name, fsm in self._fsm.items()}

    def get_plugins_info(self) -> List[dict]:
        result = []
        for name, plugin in self.plugins.items():
            fsm = self._fsm.get(name)
            if fsm:
                result.append(plugin.get_full_info(
                    state=fsm.get_state_name(),
                    error_msg=fsm.get_error_message()
                ))
        return result

    def reload_plugin_config(self, module_name: str):
        if module_name in self.plugins:
            self.plugins[module_name].reload_config()
            print(f"[PluginManager] Config for {module_name} reloaded")

    def get_plugins_count(self) -> int:
        return len(self.plugins)

    def get_plugin_object(self, module_name: str):
        return self.plugins.get(module_name)

    def get_plugin_names(self) -> List[str]:
        return list(self.plugins.keys())

    def plugin_exists(self, module_name: str) -> bool:
        return module_name in self.plugins

    def restore_states(self, states: Dict[str, str]) -> None:
        for name, target_state in states.items():
            if name not in self.plugins:
                continue
            fsm = self._get_fsm(name)
            if not fsm:
                continue
            target = None
            for state in PluginState:
                if state.value == target_state:
                    target = state
                    break
            if target is None:
                continue
            if fsm.can_transition(target):
                error_context = None
                fsm.apply_transition(target, error_context)
                self.registry.update_state(name, target.value, None)
                plugin = self.plugins[name]
                plugin._set_enabled(target == PluginState.ACTIVE)
                plugin._set_loaded(target in (PluginState.LOADED, PluginState.ACTIVE))
