# plugins/config_manager.py
import os
import json
from typing import Dict, Any

CURRENT_CONFIG_VERSION = 1


def get_config_path(module_name: str, configs_dir: str = "configs/plugins") -> str:
    if not os.path.exists(configs_dir):
        os.makedirs(configs_dir, exist_ok=True)
    return os.path.join(configs_dir, f"{module_name}.json")


def load_raw_config(module_name: str, configs_dir: str = "configs/plugins") -> Dict[str, Any]:
    config_path = get_config_path(module_name, configs_dir)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def create_default_config(module_name: str, default_config: Dict[str, Any], configs_dir: str = "configs/plugins") -> str:
    config_path = get_config_path(module_name, configs_dir)
    
    if not os.path.exists(config_path):
        full_config = {
            "config_version": CURRENT_CONFIG_VERSION,
            **default_config
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(full_config, f, indent=4, ensure_ascii=False)
        print(f"[ConfigManager] Создан конфиг для {module_name}: {config_path}")
    
    return config_path


def load_plugin_config(module_name: str, default_config: Dict[str, Any] = None, configs_dir: str = "configs/plugins") -> Dict[str, Any]:
    config_path = get_config_path(module_name, configs_dir)
    
    if not os.path.exists(config_path) and default_config is not None:
        create_default_config(module_name, default_config, configs_dir)
    
    full_config = load_raw_config(module_name, configs_dir)
    
    return {k: v for k, v in full_config.items() if k != "config_version"}


def save_plugin_config(module_name: str, config: Dict[str, Any], configs_dir: str = "configs/plugins") -> bool:
    config_path = get_config_path(module_name, configs_dir)
    
    try:
        full_config = {
            "config_version": CURRENT_CONFIG_VERSION,
            **config
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(full_config, f, indent=4, ensure_ascii=False)
        print(f"[ConfigManager] Сохранён конфиг для {module_name}")
        return True
    except Exception as e:
        print(f"[ConfigManager] Ошибка сохранения {module_name}: {e}")
        return False