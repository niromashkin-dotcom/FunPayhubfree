import sys, os, io
from datetime import datetime
try:
    _log_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _log_path = os.path.join(_log_dir, "app.log")
    # Открываем в append, line-buffered, UTF-8
    _log_file = open(_log_path, "a", encoding="utf-8", buffering=1)
    _log_file.write(f"\n\n========== START {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ==========\n")
    _log_file.flush()
    # Tee — пишем И в stdout (если консоль есть), И в файл
    class _Tee:
        def __init__(self, *streams):
            self.streams = [s for s in streams if s is not None]
        def write(self, msg):
            for s in self.streams:
                try:
                    s.write(msg)
                    s.flush()
                except Exception:
                    pass
        def flush(self):
            for s in self.streams:
                try: s.flush()
                except: pass
        def isatty(self): return False
    sys.stdout = _Tee(sys.__stdout__, _log_file)
    sys.stderr = _Tee(sys.__stderr__, _log_file)
    print(f"[B1621] File logging initialized: {_log_path}")
except Exception as _e:
    print(f"[B1621] Failed to init file logging: {_e}")

import sys
import os
import threading
import time
import logging
import signal
from pathlib import Path

print("START PROGRAM")

for k in list(os.environ.keys()):
    if k.lower() in ("http_proxy", "https_proxy", "all_proxy", "socks_proxy"):
        del os.environ[k]
os.environ["NO_PROXY"] = "*"

# ===== PERSISTENT WEBVIEW STORAGE =====
# WebView2 stores cookies/localStorage in user data folder.
# By default it uses a temp folder which can be cleared.
# We force it to use a permanent folder next to our exe/script.
if getattr(sys, 'frozen', False):
    _WV2_BASE = Path(sys.executable).resolve().parent
else:
    _WV2_BASE = Path(__file__).resolve().parent
_WV2_DATA = _WV2_BASE / "webview_data"
_WV2_DATA.mkdir(parents=True, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(_WV2_DATA)
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--disable-features=msSmartScreenProtection"
# ===== END PERSISTENT STORAGE =====


if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).resolve().parent
    INTERNAL = EXE_DIR / "_internal"
    if INTERNAL.exists():
        os.chdir(str(INTERNAL))
        sys.path.insert(0, str(INTERNAL))
        sys.path.insert(0, str(INTERNAL / "web"))
    else:
        os.chdir(str(EXE_DIR))
        sys.path.insert(0, str(EXE_DIR))
        sys.path.insert(0, str(EXE_DIR / "web"))
    CONFIGS_DIR = EXE_DIR / "configs"
    os.environ["FUNPAYHUB_CONFIGS"] = str(CONFIGS_DIR)
else:
    ROOT = Path(__file__).resolve().parent
    os.chdir(str(ROOT))
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "web"))

from flask import Flask
from web.plugin_management_api import plugin_mgmt_bp
from web.alerts_api import alerts_bp
from web.logs_api import logs_bp
from web.seller_api import seller_bp
from web.userdata_api import userdata_bp
from web.funpay_proxy import funpay_proxy_bp
from web.assistant_api import assistant_bp

print("TOKEN LOADED")

if getattr(sys, 'frozen', False):
    STATIC = str(INTERNAL / "web" / "static") if INTERNAL.exists() else str(EXE_DIR / "web" / "static")
else:
    STATIC = str(Path(__file__).resolve().parent / "web" / "static")

app = Flask(__name__, static_folder=STATIC, static_url_path="/static")
app.runtime_controller = None
app.notification_manager = None
app.runtime_log = None
app.observability = None

# ===== PLUGIN SYSTEM BOOTSTRAP =====
# Initialize clean plugin system (no Cardinal, no dashboard)
try:
    from hub_bootstrap import init_plugin_system
    hub_url = os.environ.get("FUNPAYHUB_APP_URL", "http://127.0.0.1:5000")
    _rc, _rl, _nm, _eb = init_plugin_system(plugins_dir="plugins", verbose=True, hub_url=hub_url)
    app.runtime_controller   = _rc
    app.runtime_log          = _rl
    app.notification_manager = _nm
    app.event_bus            = _eb
    print("[funpayhub_main] Plugin system bootstrap complete")
except Exception as _e:
    print(f"[funpayhub_main] Plugin bootstrap failed: {_e}")
    import traceback; traceback.print_exc()
# ===== END PLUGIN SYSTEM BOOTSTRAP =====
app.register_blueprint(plugin_mgmt_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(seller_bp)
app.register_blueprint(userdata_bp)
app.register_blueprint(funpay_proxy_bp)
app.register_blueprint(assistant_bp)

# railway.toml указывает healthcheckPath = "/health", но такого роута нигде не было
# зарегистрировано (web/health.py — пустой файл-заглушка). Без него Railway считает
# деплой нездоровым и убивает контейнер по healthcheckTimeout. Регистрируем напрямую.
@app.route("/health")
def _health():
    return "ok", 200, {"Content-Type": "text/plain"}

@app.route("/api/version")
def _api_version():
    return {"version": "2.0.0", "stage": "B", "status": "running"}

# ===== API AUTH GUARD =====
# Раньше /api/plugins/<n>/action/<action> и весь остальной внутренний API вызывались
# без всякой проверки прав — единственной защитой было то, что Flask слушал 127.0.0.1.
# Теперь, когда приложение может слушать 0.0.0.0 (headless/Railway режим), это уже
# небезопасно: любой, кто достучится до порта, может дёргать произвольные action_*
# методы любого плагина. Включаем токен через переменную окружения FUNPAYHUB_API_TOKEN.
#
# Поведение:
#   - Токен не задан И не headless (обычный desktop-режим на 127.0.0.1) — не мешаем,
#     поведение как раньше, чтобы ничего не сломать для существующих пользователей.
#   - Токен не задан, но headless (сервер, слушает 0.0.0.0) — блокируем /api/*, чтобы
#     не оставлять открытый доступ по ошибке конфигурации.
#   - Токен задан — всегда требуем заголовок X-API-Token со значением токена.
API_TOKEN = os.environ.get("FUNPAYHUB_API_TOKEN", "").strip()

@app.before_request
def _require_api_token():
    from flask import request as _req
    logger = logging.getLogger(__name__)
    path = _req.path or ""
    if not path.startswith("/api/"):
        return None  # статические файлы, /health и т.д. не защищаем
    if API_TOKEN:
        supplied = _req.headers.get("X-API-Token", "")
        if supplied != API_TOKEN:
            logger.warning(f"Invalid API token attempt from {_req.remote_addr} for path {path}")
            return {"error": "unauthorized: missing or invalid X-API-Token"}, 401
        return None
    if HEADLESS:
        logger.warning(f"Missing API token in headless mode from {_req.remote_addr} for path {path}")
        return {
            "error": "FUNPAYHUB_API_TOKEN is not set. Refusing unauthenticated access to /api/* "
                     "in server (headless) mode. Set FUNPAYHUB_API_TOKEN and pass it as the "
                     "X-API-Token header."
        }, 401
    return None
# ===== END API AUTH GUARD =====


# PORT берётся из окружения — обязательно для Railway/Docker/любого хостинга,
# который сам назначает порт через переменную $PORT. Локально (Windows desktop)
# остаётся дефолт 5000.
PORT = int(os.environ.get("PORT", 5000))

# Признаки "серверного" (headless) окружения — без GUI, без WebView2:
#   - явный флаг FUNPAYHUB_HEADLESS=1
#   - переменные, которые сами выставляют облачные платформы (Railway, Render, Docker и т.п.)
#   - Linux без DISPLAY (pywebview всё равно не сможет открыть окно)
def _is_headless() -> bool:
    if os.environ.get("FUNPAYHUB_HEADLESS", "").strip() in ("1", "true", "True"):
        return True
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_STATIC_URL"):
        return True
    if os.environ.get("RENDER") or os.environ.get("RENDER_SERVICE_ID"):
        return True
    if os.environ.get("DYNO"):  # Heroku
        return True
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return True
    return False

HEADLESS = _is_headless()
# В headless-режиме слушаем на всех интерфейсах, иначе платформа не сможет
# достучаться до контейнера. Локально для desktop-режима оставляем 127.0.0.1.
HOST = "0.0.0.0" if HEADLESS else os.environ.get("FUNPAYHUB_HOST", "127.0.0.1")

# Graceful shutdown: сигнал для всех фоновых потоков
_shutdown_event = threading.Event()

def _handle_sigterm(signum, frame):
    print(f"[funpayhub_main] Received signal {signum}, shutting down...")
    _shutdown_event.set()

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)

def run_flask():
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    from runtime.http_client import HTTPClient
    _probe_client = HTTPClient()
    probe_host = "127.0.0.1" if HOST == "0.0.0.0" else HOST
    for i in range(30):
        try:
            r = _probe_client.get(f"http://{probe_host}:{PORT}/static/dashboard.html", timeout=2)
            if r:
                break
        except Exception:
            time.sleep(1)

    if HEADLESS:
        # Сервер/контейнер: окна не будет и не должно быть — pywebview/WebView2
        # физически не может запуститься без GUI и упадёт. Просто держим процесс живым,
        # Flask (запущенный выше в отдельном потоке) обслуживает запросы.
        print(f"[funpayhub_main] Headless mode: Flask слушает {HOST}:{PORT}, GUI-окно не запускается")
        try:
            while not _shutdown_event.is_set():
                _shutdown_event.wait(1)
        except KeyboardInterrupt:
            pass
        print("[funpayhub_main] Shutdown complete")
        return

    try:
        import webview
        window = webview.create_window(
            "FunPay Hub",
            f"http://127.0.0.1:{PORT}/static/dashboard.html",
            width=1400,
            height=900,
            resizable=True,
            min_size=(1000, 600),
            text_select=True
        )
        # private_mode=False keeps localStorage between sessions
        # storage_path is also where webview keeps its own data
        try:
            webview.start(private_mode=False, storage_path=str(_WV2_DATA))
        except TypeError:
            # older pywebview without storage_path
            try:
                webview.start(private_mode=False)
            except TypeError:
                webview.start()
    except ImportError:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}/static/dashboard.html")
        try:
            while not _shutdown_event.is_set():
                _shutdown_event.wait(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
