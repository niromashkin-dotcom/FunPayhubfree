# plugins/loader.py
import os
import sys
import importlib
import inspect
from typing import Dict

from plugins.plugin_base import PluginBase

def discover_plugins(plugins_dir: str = "plugins") -> Dict[str, str]:
    plugins = {}
    if not os.path.exists(plugins_dir):
        return plugins
    for filename in os.listdir(plugins_dir):
        if filename.startswith("__"):
            continue
        if filename.endswith("_plugin.py"):
            module_name = filename[:-3]
            plugins[module_name] = os.path.join(plugins_dir, filename)
    return plugins

def load_plugin(module_name: str, plugin_manager) -> bool:
    try:
        module = importlib.import_module(f"plugins.{module_name}")
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, PluginBase) and obj is not PluginBase:
                plugin_manager.register(module_name, obj)
                return True
        print(f"[PluginLoader] ❌ {module_name}: no PluginBase class found")
        return False
    except Exception as e:
        print(f"[PluginLoader] ❌ Error loading {module_name}: {e}")
        return False

def load_plugins(plugin_manager, plugins_dir: str = "plugins") -> Dict[str, bool]:
    results = {}
    plugins = discover_plugins(plugins_dir)
    if not plugins:
        print("[PluginLoader] No plugins found")
        return results
    print(f"[PluginManager] Found {len(plugins)} plugins")
    # 1. Регистрация всех плагинов
    for module_name in plugins:
        success = load_plugin(module_name, plugin_manager)
        results[module_name] = success
    # 2. Окончательная настройка графа, проверка и загрузка
    plugin_manager.finalize_registration()
    success_count = sum(1 for v in results.values() if v)
    print(f"[PluginManager] Loaded {success_count}/{len(results)} plugins")
    return results

def reload_plugin_config(module_name: str, plugin_manager) -> bool:
    try:
        plugin_manager.reload_plugin_config(module_name)
        return True
    except Exception as e:
        print(f"[PluginLoader] ❌ Error reloading config {module_name}: {e}")
        return False