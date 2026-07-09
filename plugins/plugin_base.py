# plugins/plugin_base.py (добавлен execution_mode)
from typing import Dict, List, Optional, Any
from plugins.config_manager import load_plugin_config, save_plugin_config
from security.secrets_manager import SecretsManager

class PluginBase:
    PLUGIN_INFO: Dict[str, Any] = {
        "name": "Unnamed Plugin",
        "version": "0.0.1",
        "author": "Unknown",
        "description": "",
        "dependencies": [],
        "optional_dependencies": []
    }

    execution_mode = "inprocess"  # будет использоваться ExecutorRegistry

    def __init__(self, module_name: str, state_api, event_bus):
        self.module_name = module_name
        self.state_api = state_api
        self.event_bus = event_bus
        self.config = {}
        self.secrets = SecretsManager()
        self._enabled = False
        self._loaded = False

    def get_info(self) -> dict:
        return self.__class__.PLUGIN_INFO.copy()

    def get_dependencies(self) -> List[str]:
        return self.PLUGIN_INFO.get("dependencies", [])

    def get_optional_dependencies(self) -> List[str]:
        return self.PLUGIN_INFO.get("optional_dependencies", [])

    def on_load(self):
        pass

    def on_enable(self):
        pass

    def on_disable(self):
        pass

    def on_event(self, event):
        pass

    def on_error(self, error: Exception):
        pass

    def on_unload(self):
        pass

    def is_enabled(self) -> bool:
        return self._enabled

    def is_loaded(self) -> bool:
        return self._loaded

    def _set_enabled(self, enabled: bool):
        self._enabled = enabled

    def _set_loaded(self, loaded: bool):
        self._loaded = loaded

    def get_config(self) -> dict:
        return self.config.copy()

    def load_config(self, default_config: dict = None):
        self.config = load_plugin_config(self.module_name, default_config)
        return self.config

    def save_config(self):
        return save_plugin_config(self.module_name, self.config)

    def reload_config(self):
        self.load_config()
        print(f"[{self.module_name}] Config reloaded")
        return self.config

    def get_config_value(self, key: str, default=None):
        return self.config.get(key, default)

    def set_config_value(self, key: str, value):
        self.config[key] = value
        self.save_config()

    def get_secret(self, name: str, default: str = "") -> str:
        return self.secrets.get_secret(name, default)

    def set_secret(self, name: str, value: str) -> bool:
        return self.secrets.set_secret(name, value)

    def get_full_info(self, state: str, error_msg: str = None) -> dict:
        info = self.get_info()
        info["module"] = self.module_name
        info["state"] = state
        info["config"] = self.config
        if error_msg:
            info["error"] = error_msg
        info["dependencies"] = self.get_dependencies()
        info["optional_dependencies"] = self.get_optional_dependencies()
        info["execution_mode"] = self.execution_mode
        return info
