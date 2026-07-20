import os
import time
import json
import sqlite3
import subprocess
import requests
import psutil
from dotenv import load_dotenv
from typing import Dict, Any, List

ENV_PATH = "/opt/funpayhub/source/.env"
CONFIG_PATH = "/opt/funpayhub/source/configs/plugins/autosmm_plugin.json"
CONTROL_CONFIG_PATH = "/opt/funpayhub/source/configs/control_bot.json"

class MonitorService:
    def __init__(self):
        self._load_environment()
        self.config = self._load_control_config()

    def _load_environment(self):
        if os.path.exists(ENV_PATH):
            load_dotenv(ENV_PATH)
        else:
            load_dotenv()

    def _load_control_config(self) -> Dict[str, Any]:
        try:
            path = CONTROL_CONFIG_PATH if os.path.exists(CONTROL_CONFIG_PATH) else "configs/control_bot.json"
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "orders_db_path": "/opt/funpayhub/source/orders.db",
            "funpayhub_db_path": "/opt/funpayhub/source/funpayhub.db",
            "core_service_name": "funpayhub-core",
            "log_lines_count": 20
        }

    def get_system_resources(self) -> Dict[str, Any]:
        """Получает загрузку CPU, RAM, диска и аптайм сервера."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # RAM
            vm = psutil.virtual_memory()
            ram_used_gb = vm.used / (1024 ** 3)
            ram_total_gb = vm.total / (1024 ** 3)
            ram_percent = vm.percent
            
            # Disk
            du = psutil.disk_usage('/')
            disk_used_gb = du.used / (1024 ** 3)
            disk_total_gb = du.total / (1024 ** 3)
            disk_percent = du.percent
            
            # Uptime
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            # Форматируем аптайм в дни, часы, минуты
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            uptime_str = f"{days}д {hours}ч {minutes}м" if days > 0 else f"{hours}ч {minutes}м"
            
            return {
                "cpu": f"{cpu_percent}%",
                "ram": f"{ram_used_gb:.2f} / {ram_total_gb:.2f} GB ({ram_percent}%)",
                "disk": f"{disk_used_gb:.2f} / {disk_total_gb:.2f} GB ({disk_percent}%)",
                "uptime": uptime_str
            }
        except Exception as e:
            return {
                "cpu": "Error",
                "ram": f"Error: {e}",
                "disk": "Error",
                "uptime": "Error"
            }

    def get_funpay_balance(self) -> Dict[str, Any]:
        internal_token = os.environ.get("FUNPAYHUB_INTERNAL_TOKEN", "")
        try:
            headers = {"X-API-Token": internal_token} if internal_token else {}
            r = requests.get("http://127.0.0.1:5000/api/seller/balance/full", headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    return {"source": "core_api", "balance": data.get("balance"), "currency": data.get("currency", "RUB")}
            return {"error": f"API status {r.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_smm_balances(self) -> Dict[str, Any]:
        tb_balance = "N/A"
        looksmm_balance = "N/A"
        
        cfg_path = CONFIG_PATH if os.path.exists(CONFIG_PATH) else "configs/plugins/autosmm_plugin.json"
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                
                tb_key = cfg.get("api_key", "")
                tb_url = cfg.get("api_url", "https://twiboost.com/api/v2")
                looksmm_key = cfg.get("looksmm_api_key", "")
                looksmm_url = cfg.get("looksmm_api_url", "https://looksmm.ru/api/v2")
                
                if tb_key:
                    try:
                        r = requests.get(tb_url, params={"action": "balance", "key": tb_key}, timeout=5)
                        tb_balance = f"{r.json().get('balance')} RUB"
                    except Exception:
                        tb_balance = "Error"
                
                if looksmm_key:
                    try:
                        r = requests.get(looksmm_url, params={"action": "balance", "key": looksmm_key}, timeout=5)
                        looksmm_balance = f"{r.json().get('balance')} RUB"
                    except Exception:
                        looksmm_balance = "Error"
            except Exception as e:
                tb_balance = f"Config error"
                looksmm_balance = "Error"
                
        return {
            "twitboost": tb_balance,
            "looksmm": looksmm_balance
        }

    def get_orders_stats(self) -> Dict[str, Any]:
        db_path = self.config.get("orders_db_path", "/opt/funpayhub/source/orders.db")
        if not os.path.exists(db_path):
            return {"total": 0, "active": 0, "completed": 0, "refunded": 0}
            
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT count(*) FROM orders")
            total = c.fetchone()[0]
            
            c.execute("SELECT count(*) FROM orders WHERE status NOT IN ('completed', 'refunded', 'cancelled')")
            active = c.fetchone()[0]
            
            c.execute("SELECT count(*) FROM orders WHERE status = 'completed'")
            completed = c.fetchone()[0]
            
            c.execute("SELECT count(*) FROM orders WHERE status IN ('refunded', 'cancelled')")
            refunded = c.fetchone()[0]
            
            conn.close()
            return {
                "total": total,
                "active": active,
                "completed": completed,
                "refunded": refunded
            }
        except Exception:
            return {"total": "N/A", "active": "N/A", "completed": "N/A", "refunded": "N/A"}

    def get_lots_stats(self) -> Dict[str, Any]:
        internal_token = os.environ.get("FUNPAYHUB_INTERNAL_TOKEN", "")
        try:
            headers = {"X-API-Token": internal_token} if internal_token else {}
            r = requests.get("http://127.0.0.1:5000/api/seller/lots", headers=headers, timeout=5)
            if r.status_code == 200:
                lots = r.json()
                if isinstance(lots, list):
                    active_lots = sum(1 for l in lots if l.get("active"))
                    return {"total": len(lots), "active": active_lots}
        except Exception:
            pass
        return {"total": "N/A", "active": "N/A"}

    def deactivate_all_lots(self) -> bool:
        """Снимает все лоты с продажи через API ядра."""
        internal_token = os.environ.get("FUNPAYHUB_INTERNAL_TOKEN", "")
        try:
            headers = {"X-API-Token": internal_token} if internal_token else {}
            r = requests.post("http://127.0.0.1:5000/api/dev/lots/deactivate_all", headers=headers, json={}, timeout=10)
            return r.status_code in [200, 201]
        except Exception:
            return False

    def create_all_lots(self) -> bool:
        """Создает / публикует все лоты через API ядра."""
        internal_token = os.environ.get("FUNPAYHUB_INTERNAL_TOKEN", "")
        try:
            headers = {"X-API-Token": internal_token} if internal_token else {}
            r = requests.post("http://127.0.0.1:5000/api/lots/create_all", headers=headers, json={"dry_run": False}, timeout=15)
            return r.status_code in [200, 201]
        except Exception:
            return False

    def recreate_all_lots(self) -> bool:
        """Пересоздает все лоты (деактивация + создание)."""
        deact_ok = self.deactivate_all_lots()
        # Даем небольшую паузу ядру на обработку
        time.sleep(1)
        create_ok = self.create_all_lots()
        return deact_ok and create_ok


    def get_last_errors(self, limit: int = 15) -> List[str]:
        service_name = self.config.get("core_service_name", "funpayhub-core")
        try:
            cmd = ["journalctl", "-u", service_name, "-n", str(limit), "--no-pager"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            log_lines = res.stdout.strip().split("\n")
            
            errors = []
            for line in log_lines:
                if any(kw in line.upper() for kw in ["ERROR", "EXCEPTION", "TRACEBACK", "FAIL"]):
                    errors.append(line)
            return errors
        except Exception as e:
            return [f"Failed to fetch logs: {e}"]
