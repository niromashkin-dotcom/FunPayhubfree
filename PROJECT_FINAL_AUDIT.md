# Финальный аудит FunPayHub

Дата: 11.07.2026  
Область: Flask Hub, `tg_bot_service.py`, контракты API и подготовка к Render.

## Цепочка кнопок Telegram

| Кнопка | Callback | Endpoint / действие | Ожидаемый ответ | Статус до исправления |
|---|---|---|---|---|
| 🚀 Старт системы | `start_hub` | локальный `subprocess` | процесс Hub + доступный `/health` | Не работает для отдельного сервиса Render; успех не проверяется |
| 🛑 Стоп системы | `stop_hub` | `psutil.terminate` локального процесса | остановленный процесс | Не работает для отдельного сервиса Render |
| 📊 Отчёт сейчас | `report` | `GET /api/seller/overview` | JSON overview | Контракт существует, вывод приведён к формату |
| 📜 Логи | `logs_view` | `GET /api/logs` | JSON с записями | Контракт существует |
| 💰 Баланс | `balance` | `GET /api/seller/balance/full` | JSON balance/wallets/history | Контракт существует, был сырой JSON |
| 🔥 Симуляция | `simulation` | `POST /api/system/simulate` | `ok`, `report`, `dry_run_off` | **500:** импорт отсутствующего `runtime.simulator` |
| ⚠️ Состояние | `system_status` | `GET /api/system/health`, `GET /api/seller/overview` | health + overview | Контракты существуют |
| 📦 Лоты | `create_lots` | `POST /api/lots/generate` | сгенерированные лоты | Семантически неверно: кнопка просмотра запускала генерацию |
| 🤖 AI агент | `ai_agent` | `GET /api/system/health` | поле `ai_agent` | Контракт существует, только статус, не управление |
| 💳 Кошелёк | `wallet` | `GET /api/seller/balance/full` | balance/wallets | Контракт существует, был сырой JSON |

## Реестр проблем

| BUG | LOCATION | CAUSE | FIX | STATUS |
|---|---|---|---|---|
| Симуляция всегда завершается 500 | `web/seller_api.py: /api/system/simulate` | Импортируется отсутствующий `runtime.simulator.PluginSimulator` | Добавлен диагностический `PluginSimulator`; endpoint больше не выключает `dry_run` | FIXED |
| Кнопка «Лоты» не показывает лоты | `tg_bot_service.py: main_menu`, callback `create_lots` | Callback запускает `/api/lots/generate`, хотя существует `/api/seller/lots` | Кнопка переведена на `lots` и endpoint просмотра | FIXED |
| Start/Stop ненадёжны на Render | `tg_bot_service.py: HubController` | Bot и Hub — разные сервисы/контейнеры. `psutil` видит только свой контейнер; `subprocess` не управляет Hub и может конфликтовать за `$PORT` | Удалённый Hub больше не получает ложный успех; кнопки сообщают об ограничении и локально используют health check | PARTIALLY FIXED — для реального remote start/stop нужна отдельная авторизованная интеграция Render Deploy API |
| Успешный старт не подтверждается | `HubController.start_hub` | `Popen()` не означает, что Flask поднялся и занял порт | Добавлено ожидание `/health` до 10 секунд | FIXED |
| Сырой JSON/traceback попадает в Telegram | `tg_bot_service.py` | `market_status`, ошибки HTTP и ряд обработчиков выводят внутренние детали | JSON заменён сводкой; traceback оставлен только в server log | FIXED |
| Telegram HTML может ломаться данными FunPay | `tg_formatters.py` | Значения API вставляются без HTML-экранирования | Добавлено экранирование внешних строк | FIXED |
| Частичная утечка golden_key в лог | `runtime/seller_service.py` | В startup log выводились первые 6 символов cookie | Значение полностью удалено из лога | FIXED |
| Длительный запрос кнопки может зависать до ~15 секунд и ретраев | `HubController.call_api`, `runtime/http_client.py` | Синхронный polling handler ждёт сеть; подробная ошибка передаётся пользователю | Bot→Hub использует настраиваемый `FUNPAYHUB_API_TIMEOUT` (8 с по умолчанию) и безопасные ошибки | FIXED |
| Документация и репозиторий ориентированы на Railway, а не Render | `DEPLOYMENT*.md`, нет `render.yaml`/`Procfile` | Нет воспроизводимой конфигурации двух Render-сервисов | Добавлен `render.yaml`: один Hub web service и один Telegram worker | FIXED |
| Риск нескольких poller-экземпляров | `tg_bot_service.py` | PID-файл локален контейнеру; без единственного worker Render может создать несколько копий | Blueprint определяет один отдельный worker; масштабирование worker выше 1 запрещено операционной инструкцией | FIXED (требуется не масштабировать worker вручную) |
| Два Telegram poller в одном проекте | `plugins/telegram_notifier_plugin.py`, `tg_bot_service.py` | Notifier-плагин запускал `getUpdates` вместе с Control Panel, что приводит к Telegram 409 Conflict и непредсказуемым кнопкам | Polling notifier выключен по умолчанию; возможен лишь явно с отдельным токеном. Основной poller — только `tg_bot_service.py` | FIXED |
| Большое число подавленных исключений | `runtime/`, `plugins/`, `web/` | `except: pass` скрывает сбои, в частности в управлении плагинами | Не менять массово без сценариев; критичные места bot/API логировать и вернуть корректную ошибку | OPEN (технический долг) |
| Дублирующие модули с одинаковыми именами | `runtime/*` | Параллельные реализации `backup_manager`, `notification_manager`, `ai_team_orchestrator` повышают риск неверного импорта | Зафиксировать владельца каждого публичного импорта и удалить/перенести только после тестов | OPEN (архитектурный долг) |
| Legacy-упоминания Cardinal | `runtime/event_bus.py`, `runtime/event_types.py` | Остались значения enum `CARDINAL`, но импортов Cardinal не найдено | Оставить как совместимый enum до миграции данных; новых импортов нет | ACCEPTED |
| TODO поставщика AI-подписок | `runtime/supplier_registry.py` | Незавершённая интеграция | Не влияет на Telegram-panel; вынести в backlog | OPEN (backlog) |

## Render: требуемая конфигурация

Нужны два независимых сервиса:

1. **Web Service (Hub)**: запуск Flask/Gunicorn, health check `/health`.
2. **Background Worker (Telegram)**: только `python tg_bot_service.py`, один instance, без публичного порта.

Обеим службам требуются одинаковые значения `FUNPAYHUB_API_TOKEN`; worker также получает публичный URL Hub в `FUNPAYHUB_APP_URL`. Hub получает `GOLDEN_KEY` и `FUNPAYHUB_HEADLESS=1`; worker — `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`, `FUNPAYHUB_APP_URL`, `FUNPAYHUB_API_TOKEN`.

## Render: live-проверка 11.07.2026

Проверено через Render API и публичные endpoints:

| Сервис | ID | Тип сейчас | Start command | Health | Статус |
|---|---|---|---|---|---|
| `funpayhub` | `srv-d984konavr4c738smo4g` | `web_service` | `gunicorn funpayhub_main:app` | `/health` | live |
| `funpayhub-tg-bot` | `srv-d98e24navr4c739cq19g` | `web_service` | `python tg_bot_service.py` | встроенный `/` | live |

Фактические env-переменные найдены и заполнены: `GOLDEN_KEY`, `FUNPAYHUB_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`, `FUNPAYHUB_APP_URL=https://funpayhub.onrender.com`, supplier API keys. Значения секретов не выведены в аудит.

Публичные endpoints Hub на текущем проде:

| Endpoint | HTTP | Статус prod | Вывод |
|---|---:|---|---|
| `/health` | GET | 200 | ok |
| `/api/system/health` | GET | 200 | warning: нет backup и части config-файлов |
| `/api/seller/overview` | GET | 200 | FunPay подключен, user `nikitchxdd` |
| `/api/seller/balance/full` | GET | 200 | баланс 0 RUB/USD/EUR |
| `/api/seller/lots` | GET | 200 | найден 1 лот |
| `/api/logs` | GET | 200 | логи отдаются |
| `/api/system/simulate` | POST | 500 | `No module named 'runtime.simulator'` на проде, локальный фикс еще не задеплоен |

Прод-логи подтвердили:

- `409 Conflict: terminated by other getUpdates request` был в логах Telegram polling.
- `TelegramNotifierPlugin` запускал собственный polling параллельно с `tg_bot_service.py`; локальный фикс отключает это по умолчанию.
- Бот на проде пишет `Hub is not running`, хотя Hub отвечает 200. Это старое поведение проверки локального процесса; локальный фикс переводит удаленный Hub на health-check.
- В прод-логах есть частичная утечка `golden_key=...`; локальный фикс уже убирает печать значения.
- В Hub-логах есть повторяющиеся обращения к `http://127.0.0.1:5000/...`, которые не работают на Render-сервисе с Gunicorn на `$PORT`. Это отдельный production-долг для внутренних URL runtime/plugin-кода.

После выкладки локальных исправлений нужно повторить live-проверку Render: `/api/system/simulate` должен стать 200, в логах не должно быть `409 Conflict`, `TelegramNotifierPlugin polling started` и печати `golden_key=...`.

## Проверки

- Поиск импортов FunPay Cardinal: активных импортов не найдено.
- Синтаксис всех Python-файлов: `python -m compileall -q .` — PASS после исправлений.
- Регрессионные тесты: `python -m pytest -q tests` — **9 passed**.
- Flask test client с API-auth проверил: `/health`, `/api/seller/overview`, `/api/seller/balance/full`, `/api/seller/lots`, `/api/system/health`, `/api/logs`, `/api/system/simulate` — все ответили без 5xx.
- Контрактный тест проверяет, что все 10 кнопок главного меню имеют handler, а форматтеры не отдают raw JSON.
- Реальное нажатие в Telegram и логи удалённого Render недоступны из локального рабочего каталога. После deploy необходимо проверить worker log: один `infinity_polling`, без `409 Conflict`, и оба сервиса в состоянии Live.
