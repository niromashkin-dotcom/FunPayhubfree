# plugins/plugin_registry.py
from typing import Dict, List, Optional
from plugins.plugin_state import PluginState


class PluginRegistry:
    """
    Реестр метаданных плагинов.
    Не хранит объекты плагинов, только метаданные и состояния.
    """
    
    def __init__(self):
        self._metadata: Dict[str, dict] = {}
        self._states: Dict[str, str] = {}
        self._errors: Dict[str, str] = {}
    
    def register_metadata(self, module_name: str, metadata: dict) -> bool:
        if module_name in self._metadata:
            print(f"[PluginRegistry] Метаданные для {module_name} уже зарегистрированы")
            return False
        
        self._metadata[module_name] = {
            "name": metadata.get("name", module_name),
            "version": metadata.get("version", "0.0.1"),
            "author": metadata.get("author", "Unknown"),
            "description": metadata.get("description", "")
        }
        self._states[module_name] = PluginState.INIT.value
        print(f"[PluginRegistry] Зарегистрирован плагин: {module_name}")
        return True
    
    def update_state(self, module_name: str, state: str, error_msg: str = None) -> bool:
        if module_name not in self._metadata:
            print(f"[PluginRegistry] Плагин {module_name} не найден")
            return False
        
        self._states[module_name] = state
        if error_msg:
            self._errors[module_name] = error_msg
        elif state != PluginState.ERROR.value:
            self._errors.pop(module_name, None)
        return True
    
    def get_plugin(self, module_name: str) -> Optional[dict]:
        if module_name not in self._metadata:
            return None
        
        return {
            "module": module_name,
            "name": self._metadata[module_name]["name"],
            "version": self._metadata[module_name]["version"],
            "author": self._metadata[module_name]["author"],
            "description": self._metadata[module_name]["description"],
            "state": self._states.get(module_name, PluginState.INIT.value),
            "error": self._errors.get(module_name)
        }
    
    def get_all_plugins(self) -> List[dict]:
        return [self.get_plugin(name) for name in self._metadata.keys()]
    
    def get_plugins_count(self) -> int:
        return len(self._metadata)
    
    def get_plugin_state(self, module_name: str) -> Optional[str]:
        return self._states.get(module_name)
    
    def plugin_exists(self, module_name: str) -> bool:
        return module_name in self._metadata