# Архитектура БД (Database Schema)

Проект использует SQLite в режиме WAL (Write-Ahead Logging).
Модели описаны через SQLAlchemy в `runtime/database/models.py`.

## Основные таблицы:

### 1. `orders`
- **id** (Integer, PK)
- **funpay_order_id** (String, Unique)
- **buyer_id** (String)
- **lot_id** (String)
- **status** (String: NEW, PAID, PROCESSING, DELIVERED, COMPLETED, FAILED)
- **created_at**, **paid_at**, **completed_at**

### 2. `transactions` (Ledger)
- **id** (Integer, PK)
- **order_id** (String, FK к orders.funpay_order_id)
- **tx_type** (String: SALE, PROVIDER_COST, COMMISSION, PROFIT)
- **amount** (Float)
- **created_at**
*Правило: Профит = SUM(SALE) - SUM(PROVIDER_COST) - SUM(COMMISSION).*

### 3. `event_journal`
- **id** (Integer, PK)
- **event_type** (String)
- **payload** (Text JSON)
- **status** (String: PENDING, PROCESSING, PROCESSED, FAILED)
- **created_at**, **processed_at**
*Используется для Crash Recovery. Все события проходят через этот журнал.*
