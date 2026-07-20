# e:\Projects\FunPayHub\control_bot\monitor.py
import os
import re
import json
import sqlite3
import subprocess
import requests
from dotenv import load_dotenv

# Пути к файлам по умолчанию
ENV_PATH = "/opt/funpayhub/source/.env"
CONFIG_PATH = "/opt/funpayhub/source/configs/plugins/autosmm_plugin.json"
CONTROL_CONFIG_PATH = "/opt/funpayhub/source/configs/control_bot.json"

def load_environment():
    """Загружает .env файл ядра."""
    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH)
    else:
        # Локальная отладка
        load_dotenv()

def get_control_config() -> dict:
    """Загружает конфигурацию контрольного бота."""
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

def get_core_status() -> dict:
    """Получает статус службы ядра через systemctl."""
    cfg = get_control_config()
    service_name = cfg.get("core_service_name", "funpayhub-core")
    try:
        # Получаем свойства службы
        cmd = ["systemctl", "show", service_name, "--property=ActiveState,SubState,MainPID,ActiveEnterTimestamp"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        props = {}
        for line in res.stdout.strip().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
        
        return {
            "name": service_name,
            "active": props.get("ActiveState") == "active",
            "status": props.get("ActiveState", "unknown"),
            "sub_status": props.get("SubState", ""),
            "pid": props.get("MainPID", "0"),
            "uptime": props.get("ActiveEnterTimestamp", "")
        }
    except Exception as e:
        return {
            "name": service_name,
            "active": False,
            "status": "error",
            "sub_status": str(e),
            "pid": "0",
            "uptime": ""
        }

def get_funpay_balance() -> dict:
    """Получает баланс FunPay через API ядра или напрямую через FunPayAPI."""
    load_environment()
    internal_token = os.environ.get("FUNPAYHUB_INTERNAL_TOKEN", "")
    
    # 1. Пробуем запросить через API ядра
    try:
        headers = {"X-API-Token": internal_token} if internal_token else {}
        r = requests.get("http://127.0.0.1:5000/api/seller/balance/full", headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Достаем баланс
            if isinstance(data, dict):
                return {"source": "core_api", "balance": data.get("balance"), "currency": data.get("currency", "RUB")}
    except Exception:
        pass

    # 2. Fallback: Прямой запрос через FunPayAPI
    golden_key = os.environ.get("FUNPAY_GOLDEN_KEY", "")
    user_agent = os.environ.get("FUNPAY_USER_AGENT", "Mozilla/5.0")
    if golden_key:
        try:
            # Импортируем FunPayAPI
            from FunPayAPI.account import Account
            acc = Account(golden_key, user_agent=user_agent)
            # Запрашиваем продажи, чтобы получить актуальный баланс или парсим главную страницу
            # Для простоты спарсим баланс через внутренний запрос
            response = acc.method("get", "", {}, {}, raise_not_200=True)
            html = response.content.decode("utf-8", errors="ignore")
            # Находим баланс в шапке
            # <span class="badge badge-balance">70.00 ₽</span>
            match = re.search(r'class="badge badge-balance">([\d\.\s]+)\s*([₽$€])', html)
            if match:
                val = match.group(1).replace(" ", "")
                curr = "RUB" if match.group(2) == "₽" else match.group(2)
                return {"source": "direct_parse", "balance": val, "currency": curr}
        except Exception as e:
            return {"source": "error", "error": f"Direct parse error: {e}"}
            
    return {"source": "unknown", "error": "No credentials available or Core API is offline."}

def get_smm_balances() -> dict:
    """Получает балансы TwitBoost и LookSMM напрямую по их API ключам."""
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
            
            # Запрос TwitBoost
            if tb_key:
                try:
                    r = requests.get(tb_url, params={"action": "balance", "key": tb_key}, timeout=5)
                    tb_balance = f"{r.json().get('balance')} RUB"
                except Exception:
                    tb_balance = "Error"
            
            # Запрос LookSMM
            if looksmm_key:
                try:
                    r = requests.get(looksmm_url, params={"action": "balance", "key": looksmm_key}, timeout=5)
                    looksmm_balance = f"{r.json().get('balance')} RUB"
                except Exception:
                    looksmm_balance = "Error"
        except Exception as e:
            tb_balance = f"Config error: {e}"
            looksmm_balance = "Error"
            
    return {
        "twitboost": tb_balance,
        "looksmm": looksmm_balance
    }

def get_orders_stats() -> dict:
    """Считывает статистику заказов из orders.db."""
    cfg = get_control_config()
    db_path = cfg.get("orders_db_path", "/opt/funpayhub/source/orders.db")
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

def get_lots_stats() -> dict:
    """Считывает статистику лотов из API ядра."""
    load_environment()
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

def get_last_errors() -> list:
    """Считывает последние ошибки из логов службы ядра через journalctl."""
    cfg = get_control_config()
    service_name = cfg.get("core_service_name", "funpayhub-core")
    lines_count = cfg.get("log_lines_count", 20)
    try:
        cmd = ["journalctl", "-u", service_name, "-n", str(lines_count), "--no-pager"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log_lines = res.stdout.strip().split("\n")
        
        # Фильтруем строки с ERROR, Exception, Traceback
        errors = []
        for line in log_lines:
            if any(kw in line.upper() for kw in ["ERROR", "EXCEPTION", "TRACEBACK", "FAIL"]):
                errors.append(line)
        return errors
    except Exception as e:
        return [f"Failed to fetch logs: {e}"]
