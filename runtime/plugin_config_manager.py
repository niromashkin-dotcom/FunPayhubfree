import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class PluginConfigManager:
    def __init__(self, config_dir: str = "configs/plugins"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.configs = {}
        self.load_all_configs()
    
    def load_all_configs(self):
        '''Загрузить все конфиги плагинов'''
        for config_file in self.config_dir.glob("*.json"):
            plugin_name = config_file.stem
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.configs[plugin_name] = json.load(f)
            except Exception as e:
                print(f"Failed to load config for {plugin_name}: {e}")
    
    def get_config(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        '''Получить конфиг плагина'''
        return self.configs.get(plugin_name)
    
    def update_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        '''Обновить конфиг плагина'''
        try:
            # Validate JSON
            json.dumps(config)
            
            # Save to file
            config_file = self.config_dir / f"{plugin_name}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Update in memory
            self.configs[plugin_name] = config
            return True
        except Exception as e:
            print(f"Failed to update config for {plugin_name}: {e}")
            return False
    
    def create_default_config(self, plugin_name: str) -> Dict[str, Any]:
        '''Создать дефолтный конфиг'''
        default = {
            "enabled": False,
            "priority": 10,
            "config": {}
        }
        self.update_config(plugin_name, default)
        return default
    
    def validate_config(self, plugin_name: str, config: Dict[str, Any]) -> tuple:
        '''Валидировать конфиг'''
        required_fields = ["enabled", "priority", "config"]
        
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"
        
        if not isinstance(config["enabled"], bool):
            return False, "Field 'enabled' must be boolean"
        
        if not isinstance(config["priority"], int):
            return False, "Field 'priority' must be integer"
        
        if not isinstance(config["config"], dict):
            return False, "Field 'config' must be object"
        
        return True, "OK"
