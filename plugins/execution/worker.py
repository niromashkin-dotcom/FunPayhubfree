# plugins/execution/worker.py
import sys
import time
import threading
from importlib import import_module

_plugin = None
_heartbeat_queue = None
_plugin_class = None

def send_heartbeat():
    global _heartbeat_queue
    while True:
        time.sleep(5)
        if _heartbeat_queue:
            try:
                _heartbeat_queue.put(("heartbeat", time.time()))
            except:
                pass

def load_plugin(module_name, plugin_cls):
    global _plugin, _plugin_class
    if _plugin is not None:
        return
    try:
        # Если передан класс плагина – используем его
        if plugin_cls:
            _plugin = plugin_cls(module_name, None, None)
        else:
            # fallback: импортируем модуль
            module = import_module(f"plugins.{module_name}")
            from plugins.plugin_base import PluginBase
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if isinstance(obj, type) and issubclass(obj, PluginBase) and obj is not PluginBase:
                    _plugin = obj(module_name, None, None)
                    break
        if _plugin is None:
            raise Exception(f"No PluginBase subclass found in {module_name}")
    except Exception as e:
        print(f"Worker: Failed to load plugin {module_name}: {e}")
        raise

def worker_main(module_name, event_queue, result_queue, plugin_cls=None):
    global _heartbeat_queue
    _heartbeat_queue = result_queue
    # Запускаем поток heartbeat
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        load_plugin(module_name, plugin_cls)
        while True:
            cmd, event_name, data = event_queue.get()
            if cmd == "stop":
                break
            elif cmd == "event":
                try:
                    result = _plugin.on_event(event_name, data)
                    result_queue.put(result)
                except Exception as e:
                    result_queue.put(e)
    except Exception as e:
        result_queue.put(e)
