# plugins/plugin_state.py
from enum import Enum
from typing import Dict, Set, Optional
from dataclasses import dataclass


class PluginState(Enum):
    INIT = "init"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    UNLOADED = "unloaded"


ALLOWED_TRANSITIONS: Dict[PluginState, Set[PluginState]] = {
    PluginState.INIT: {PluginState.LOADED, PluginState.ERROR, PluginState.UNLOADED},
    PluginState.LOADED: {PluginState.ACTIVE, PluginState.DISABLED, PluginState.ERROR, PluginState.UNLOADED},
    PluginState.ACTIVE: {PluginState.DISABLED, PluginState.ERROR, PluginState.UNLOADED},
    PluginState.DISABLED: {PluginState.ACTIVE, PluginState.ERROR, PluginState.UNLOADED},
    PluginState.ERROR: {PluginState.UNLOADED},
    PluginState.UNLOADED: set(),
}


@dataclass
class PluginErrorContext:
    message: str
    original_exception: Exception = None
    
    def to_string(self) -> str:
        if self.original_exception:
            return f"{self.message}: {self.original_exception}"
        return self.message


class PluginStateMachine:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self._state = PluginState.INIT
        self._error_context: Optional[PluginErrorContext] = None
    
    def get_state(self) -> PluginState:
        return self._state
    
    def get_state_name(self) -> str:
        return self._state.value
    
    def get_error_context(self) -> Optional[PluginErrorContext]:
        return self._error_context
    
    def get_error_message(self) -> Optional[str]:
        return self._error_context.to_string() if self._error_context else None
    
    def can_transition(self, target_state: PluginState) -> bool:
        return target_state in ALLOWED_TRANSITIONS.get(self._state, set())
    
    def apply_transition(self, target_state: PluginState, error_context: PluginErrorContext = None) -> bool:
        if not self.can_transition(target_state):
            print(f"[FSM] {self.module_name}: запрещён переход {self._state.value} → {target_state.value}")
            return False
        
        old_state = self._state
        self._state = target_state
        self._error_context = error_context if target_state == PluginState.ERROR else None
        
        print(f"[FSM] {self.module_name}: {old_state.value} → {target_state.value}")
        return True