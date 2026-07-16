# Результаты тестирования (Delivery & Payment Flow)

Все критические E2E (End-to-End) тесты на симуляцию работы с заказами пройдены успешно.
Тесты запускаются командой `pytest tests/test_delivery_and_payment_flow.py -v`.

## Результат последнего прогона

```text
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Projects\FunPayHub
plugins: anyio-4.12.1
collecting ... collected 5 items

tests/test_delivery_and_payment_flow.py::test_scenario_1_success PASSED  [ 20%]
tests/test_delivery_and_payment_flow.py::test_scenario_2_provider_timeout PASSED [ 40%]
tests/test_delivery_and_payment_flow.py::test_scenario_3_crash_recovery PASSED [ 60%]
tests/test_delivery_and_payment_flow.py::test_scenario_4_double_payment PASSED [ 80%]
tests/test_delivery_and_payment_flow.py::test_scenario_5_cce_unavailable PASSED [100%]

============================== 5 passed in 8.14s ==============================
```

## Покрытие сценариев

1. **`test_scenario_1_success`**: Проверка полного цикла Оплата -> Доставка -> CCE (клиенту ушло сообщение) -> Ledger (записана прибыль).
2. **`test_scenario_2_provider_timeout`**: Проверка отмены. Провайдер не отдал ключ, заказ переходит в FAILED, прибыль в Ledger не начисляется.
3. **`test_scenario_3_crash_recovery`**: Сервер падает посреди оплаты. При рестарте `EventJournal` находит `order_paid` и досылает событие -> Клиент все равно получает товар.
4. **`test_scenario_4_double_payment`**: Идемпотентность (Idempotency check). При 3-кратном срабатывании вебхука об оплате одного заказа, Ledger начисляет продажу только ОДИН раз, дублей товаров не выдается.
5. **`test_scenario_5_cce_unavailable`**: Товар выдан поставщиком, но серверу CCE не удалось отправить сообщение в чат. Статус остается `PROCESSING` (DELIVERY_PENDING), чтобы не потерять товар, админ получает ALARM.
