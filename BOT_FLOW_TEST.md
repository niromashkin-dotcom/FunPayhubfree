# BOT FLOW TEST DOCUMENTATION

## Overview

This document covers all Telegram bot flows in `tg_bot_service.py`.  
Each flow documents the button/command, the Python function invoked, the API endpoint called (if any), and the expected result.

---

## Commands

| Command | Function | Description | Expected Result |
|---------|----------|-------------|-----------------|
| `/start` or `/menu` | `cmd_start()` | Show main menu with all control buttons | Bot replies with "FunPayHub Control Panel" + inline keyboard |
| `/auth <password>` | `cmd_auth()` | Authorize user via bcrypt password | Success: "✅ Авторизация успешна!" + user saved to whitelist. Failure: "❌ Неверный пароль." |
| `/ping` | `cmd_ping()` | Health check for the bot itself | Bot replies "pong ✅" |

---

## Main Menu Buttons

### 🚀 Старт системы (start_hub)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.start_hub()` |
| **API Endpoint** | None (local process management) |
| **Expected Result** | "🚀 FunPay Hub запущен" — starts `funpayhub_main.py` as subprocess |
| **Error Case** | "🚀 Ошибка: Hub уже запущен" or exception traceback |

### 🛑 Стоп системы (stop_hub)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.stop_hub()` |
| **API Endpoint** | None (local process management) |
| **Expected Result** | "🛑 FunPay Hub остановлен" — terminates hub subprocess |
| **Error Case** | "🛑 Ошибка: Hub не запущен" or exception traceback |

### 📊 Отчёт сейчас (report)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/api/seller/overview")` |
| **API Endpoint** | `GET /api/seller/overview` |
| **Expected Result** | "📋 Отчёт:" + JSON overview data |
| **Error Case** | "❌ Hub не отвечает" or exception traceback |

### 📜 Логи (logs_view)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/logs")` |
| **API Endpoint** | `GET /dashboard/api/logs` |
| **Expected Result** | "📜 Логи:" + formatted log lines with filter/refresh keyboard |
| **Error Case** | "❌ Не удалось загрузить логи" or exception traceback |

### 💰 Баланс (balance)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/api/seller/balance/full")` |
| **API Endpoint** | `GET /api/seller/balance/full` |
| **Expected Result** | "💰 Баланс:" + JSON balance data |
| **Error Case** | "❌ Hub не отвечает" or exception traceback |

### 🔥 Симуляция (simulation)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/run_simulation")` |
| **API Endpoint** | `POST /dashboard/api/run_simulation` |
| **Expected Result** | "🧪 Симуляция:" + JSON simulation results |
| **Error Case** | "❌ Ошибка:" + exception traceback |

### ⚠️ Состояние (system_status)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/api/system/health")` and `/api/seller/overview` |
| **API Endpoint** | `GET /api/system/health`, `GET /api/seller/overview` |
| **Expected Result** | "🔧 Состояние системы:" with FunPay connection status, hub health, warnings, backup count |
| **Error Case** | "❌ Ошибка в обработчике состояния" + traceback |

### 📦 Лоты (create_lots)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/generate_lots", POST, {...})` |
| **API Endpoint** | `POST /dashboard/api/generate_lots` |
| **Expected Result** | "📦 {message}" — lots generated (dry_run: true) |
| **Error Case** | "❌ {result}" or exception traceback |

### 🤖 AI агент (ai_agent)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/api/ai/status")` |
| **API Endpoint** | `GET /api/ai/status` |
| **Expected Result** | "🤖 AI Agent статус:" + JSON status data |
| **Error Case** | "❌ {result}" or exception traceback |

### 💳 Кошелёк (wallet)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/api/wallet/balance")` |
| **API Endpoint** | `GET /api/wallet/balance` |
| **Expected Result** | "💳 Кошелёк:\nБаланс: X.XX ₽" + JSON details |
| **Error Case** | "❌ {result}" or exception traceback |

---

## Logs Submenu

### 🔴 Только ошибки (logs_filter_errors)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/logs?level=ERROR")` |
| **API Endpoint** | `GET /dashboard/api/logs?level=ERROR` |
| **Expected Result** | Log entries filtered to ERROR level only |

### 🟡 Только предупреждения (logs_filter_warnings)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/logs?level=WARNING")` |
| **API Endpoint** | `GET /dashboard/api/logs?level=WARNING` |
| **Expected Result** | Log entries filtered to WARNING level only |

### 🔵 Все (logs_filter_all)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/logs")` |
| **API Endpoint** | `GET /dashboard/api/logs` |
| **Expected Result** | All log entries (no filter) |

### 🔄 Обновить (logs_refresh)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/logs")` |
| **API Endpoint** | `GET /dashboard/api/logs` |
| **Expected Result** | Refreshed log entries |

### ⬅️ Назад (back_to_menu)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> inline edit |
| **API Endpoint** | None |
| **Expected Result** | Returns to "🎮 FunPay Hub Control Panel" main menu |

---

## Plugins Submenu

### Плагины (plugins_panel)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/plugins/summary")` |
| **API Endpoint** | `GET /dashboard/api/plugins/summary` |
| **Expected Result** | "🔌 Плагины:" with АвтоСММ and АвтоДонат status + lot counts |

### АвтоСММ / АвтоДонат detail (autosmm / autodonate)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api(f"/dashboard/api/plugins/{cmd}/status")` |
| **API Endpoint** | `GET /dashboard/api/plugins/{plugin}/status` |
| **Expected Result** | Plugin name, status (🟢/🔴), orders count, errors |

### ▶️ / ⏹️ Toggle (autosmm_toggle / autodonate_toggle)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api(f"/dashboard/api/plugins/{plugin}/toggle", POST)` |
| **API Endpoint** | `POST /dashboard/api/plugins/{plugin}/toggle` |
| **Expected Result** | "✅ {Plugin} запущен/остановлен" |

### 🚫 Деактивировать лоты (autosmm_deactivate / autodonate_deactivate)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api(f"/dashboard/api/plugins/{plugin}/deactivate_lots", POST)` |
| **API Endpoint** | `POST /dashboard/api/plugins/{plugin}/deactivate_lots` |
| **Expected Result** | "🗑️ Снято лотов: {count}" |

### 📊 Статус (autosmm_status / autodonate_status)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api(f"/dashboard/api/plugins/{plugin}/status")` |
| **API Endpoint** | `GET /dashboard/api/plugins/{plugin}/status` |
| **Expected Result** | "📊 Статус {Plugin}:" + JSON status data |

---

## Other Flows

### 🗑️ Remove All Lots (remove_all_lots)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/dashboard/api/remove_lots", POST, {...})` |
| **API Endpoint** | `POST /dashboard/api/remove_lots` |
| **Expected Result** | "🗑️ Лоты сняты!" with counts per plugin |

### ✅ Auto-create Toggle (auto_create_toggle)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> `controller.call_api("/api/plugins/autosmm/toggle_auto", POST, {...})` |
| **API Endpoint** | `POST /api/plugins/autosmm/toggle_auto` |
| **Expected Result** | "✅ Авто-создание включено/выключено" |

### ⚙️ Settings (settings)
| Field | Value |
|-------|-------|
| **Function** | `callback_handler()` -> inline text |
| **API Endpoint** | None |
| **Expected Result** | "⚙ Настройки пока не реализованы." (placeholder) |

---

## Internal API (HubController)

| Method | Description |
|--------|-------------|
| `is_hub_running()` | Checks if `funpayhub_main.py` process is active via `psutil` |
| `start_hub()` | Launches hub as subprocess with `subprocess.Popen` |
| `stop_hub()` | Terminates hub process via `psutil.Process.terminate()` |
| `call_api(endpoint, method, payload)` | Calls hub HTTP API with `X-API-Token` auth header |

---

## Scheduled Reports (ReportEngine)

| Report | Time (MSK) | Function | Description |
|--------|-----------|----------|-------------|
| Daily Report | 06:00 | `send_daily_report()` | Orders count, income, expenses, profit, breakdown by type |
| Evening Summary | 21:00 | `send_evening_summary()` | Daily report + forecast: avg profit/day, weekly/monthly projections, provider stats |

Reports are sent to `admin_chat_id` via Telegram API (`https://api.telegram.org/bot{token}/sendMessage`).
