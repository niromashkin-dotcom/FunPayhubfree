# PROJECT_AUDIT.md — Технический аудит FunPayHub

> Дата: 2026-07-11  
> Версия проекта: 2.0.0  

---

## Краткое резюме

FunPayHub — комплексный проект автоматизации работы продавца на FunPay.ru.
Включает:
- **funpayhub_main.py** — Flask веб-приложение (хаб), запускается как отдельный Render-сервис
- **tg_bot_service.py** — Telegram бот управления, второй Render-сервис  
- **runtime/seller_service.py** — синглтон с бизнес-логикой работы с FunPay API
- **plugins/** — плагины (AutoSMM, AutoDonate, AutoBump, TelegramNotifier и др.)

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ (исправлены)

### 1. golden_key не читался из ENV на Render
**Исправление:** Метод `load_credentials()` теперь проверяет ENV переменные `GOLDEN_KEY` как fallback.

### 2. FUNPAYHUB_API_TOKEN не совпадал между сервисами
**Исправление:** Убран хардкод фолбека `fhp_api_token_2026_change_me_later` в `tg_bot_service.py`, токен читается из ENV.

### 3. Обработчик system_status ожидал несуществующие поля
**Исправление:** Обработчик переписан — корректно отображает `status` из `/api/system/health` и проверяет `/api/seller/overview`.

### 4. GOLDEN_KEY отсутствовал в Render env vars сервиса funpayhub
**Исправление:** Добавлен актуальный `GOLDEN_KEY` в Render.

---

## 🟡 ВАЖНЫЕ ПРОБЛЕМЫ (в процессе исправления)

### 5. HTTPClient с 5 retry создаёт задержки до 62 секунд
**Рекомендация:** В `tg_bot_service.call_api()` использовать `HTTPClient(max_retries=1)` для интерактивных запросов.

### 6. HubController.start_hub пытается запустить процесс через subprocess на Render
**Рекомендация:** Кнопка "Старт/Стоп системы" на Render должна обращаться к Render API для рестарта сервиса.

### 7. Два сервиса Telegram Bot (409 Conflict)
**Статус:** `telegram_notifier_plugin` и `tg_bot_service` используют один токен.

### 8. Отсутствие reconnect при потере соединения с FunPay
**Рекомендация:** Добавить TTL для кэша аккаунта или сброс при получении HTTP 401.

---

## 🟢 ОСТАЛЬНЫЕ НАБЛЮДЕНИЯ

### 9. Фоновые потоки без обработки исключений
В `hub_bootstrap.py` потоки `MarketAutoUpdate`, `HealthCheck`, `AutoBackup` запускаются как daemon.

### 10. Race condition в seller_service._get_account()
`_get_account()` проверяет `self._account is not None` без блокировки.

### 11. Жёстко заданный порт 5000 в hub_bootstrap.py
Использовать `os.environ.get('PORT', 5000)`.
