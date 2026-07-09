# plugins/logger_plugin.py
from plugins.plugin_base import PluginBase

class LoggerPlugin(PluginBase):
    PLUGIN_INFO = {
        "name": "Logger Plugin",
        "version": "1.0.0",
        "author": "FunPay Hub",
        "description": "Логирует все события в консоль",
        "default_config": {
            "log_balance": True,
            "log_lots": True,
            "log_logs": True
        }
    }
    
    def on_init(self):
        print("[LoggerPlugin] 🟡 INIT")
    
    def on_load(self):
        self.load_config(self.PLUGIN_INFO.get("default_config", {}))
        print("[LoggerPlugin] ✅ LOADED")
    
    def on_enable(self):
        print("[LoggerPlugin] 🟢 ACTIVE")
    
    def on_disable(self):
        print("[LoggerPlugin] ⚫ DISABLED")
    
    def on_error(self, error):
        print(f"[LoggerPlugin] 🔴 ERROR: {error}")
    
    def on_unload(self):
        print("[LoggerPlugin] ⚪ UNLOADED")
    
    def on_event(self, event_name, data):
        if event_name == "balance_updated" and self.config.get("log_balance", True):
            print(f"[LoggerPlugin] 💰 Баланс: {data}")
        elif event_name == "lots_updated" and self.config.get("log_lots", True):
            count = len(data) if data else 0
            print(f"[LoggerPlugin] 📦 Лотов: {count}")
        elif event_name == "log_added" and self.config.get("log_logs", True):
            print(f"[LoggerPlugin] 📝 {data}")