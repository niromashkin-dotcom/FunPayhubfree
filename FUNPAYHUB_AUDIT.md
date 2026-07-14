# FunPayHub Full Project Audit Report

> Automated static analysis. Line numbers refer to original source files.

---

## AUDIT SESSION: 2026-07-13 → 2026-07-14

### Summary
This session fixed critical data integrity issues in the reporting system and Telegram bot UI. All changes were committed and deployed to Render.

---

## 6. Report System Data Source Fix (2026-07-13)

### Problem
Evening report at 21:00 showed **11106 orders** with **150 ₽** revenue (0.013 ₽ per order — impossible). Test/simulation orders were included in reports.

### Solution

#### 6.1 Added `source` field to Order model
**File:** `runtime/database/models.py`
```python
source = Column(String(32), default="real", nullable=False, index=True)
```

#### 6.2 Updated Repository.create_order()
**File:** `runtime/database/repository.py`
```python
def create_order(..., source: str = "real") -> Order:
    order = Order(..., source=source)
```

#### 6.3 Filtered Ledger queries
**File:** `runtime/database/ledger.py`
```python
def get_balance_snapshot(..., real_only: bool = True):
    if real_only:
        query = query.join(Order, Transaction.order_id == Order.id)
        query = query.filter(Order.source == "real")

def get_daily_report(..., real_only: bool = True):
    query = session.query(func.count(Order.id)).filter(...)
    if real_only:
        query = query.filter(Order.source == "real")
```

#### 6.4 Updated dashboard stats
**File:** `runtime/database/repository.py`
```python
total_orders = session.query(func.count(Order.id)).filter(Order.source == "real").scalar() or 0
total_income = session.query(func.sum(Transaction.amount)).join(Order, ...).filter(Order.source == "real").scalar() or 0.0
```

#### 6.5 Added data source annotations
**File:** `runtime/report_engine.py`
```python
f"📦 Заказов: {orders}"
f"   Источник: orders.db WHERE source='real' AND started_at в периоде"
f"💰 Доход: {income:.2f} ₽"
f"   Источник: transactions WHERE type='funpay_income' + JOIN orders(source='real')"
```

#### 6.6 Automatic DB migration
**File:** `runtime/database/base.py`
```python
def _migrate_add_order_source(engine):
    conn.execute("ALTER TABLE orders ADD COLUMN source VARCHAR(32) DEFAULT 'real' NOT NULL")
    _mark_existing_test_orders(conn)  # sim_*, ORD*, db_stress_* → simulation
```

#### 6.7 Updated test scripts
**File:** `scripts/run_simulation.py`
```python
order = repo.create_order(..., source="simulation")
```
**File:** `scripts/acceptance_test.py`
```python
repo.create_order(..., source="acceptance_test")
```

#### 6.8 Restored SupplierOrderRegistry
**File:** `runtime/order_tracker.py`
- Restored class for plugin idempotency
- Fixed `autosmm_plugin` and `autodonate_plugin` imports

### Results
- Reports now show only real orders
- Each field has source annotation
- Dashboard displays accurate statistics
- Lot scaling based on real sales only

### Commits
- `b533697` - fix(reports): exclude simulation/test data from reports
- `56662f2` - docs(audit): add report system data sources fix section
- `95d7acc` - docs(audit): complete report system audit with full details

---

## 7. Telegram Bot UI and Auto-Refresh Fixes (2026-07-14)

### 7.1 Fixed duplicate menu text
**File:** `bot/handlers/callbacks.py`
```python
# Before:
await _safe_edit(query, "🛒 <b>Управление лотами</b>\n─" * 18 + "\nВыберите действие:", get_lots_menu())
# After:
await _safe_edit(query, "🛒 <b>Управление лотами</b>\n" + "─" * 40 + "\nВыберите действие:", get_lots_menu())
```

### 7.2 Fixed plugin callback mismatch
**File:** `bot/keyboards/main.py`
```python
def get_plugin_detail_keyboard(plugin_name: str, is_active: bool):
    alias = "autosmm" if plugin_name == "autosmm_plugin" else "autodonate" if plugin_name == "autodonate_plugin" else plugin_name
    action = "⏹️ Остановить" if is_active else "▶️ Запустить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=action, callback_data=f"{alias}_toggle")],
        ...
    ])
```

### 7.3 Added CPU/RAM to health check
**File:** `runtime/seller_service.py`
```python
def check_system_health(self) -> dict:
    ...
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory_percent = psutil.virtual_memory().percent
    except Exception:
        pass
    return {
        ...
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
    }
```

### 7.4 Fixed auto-refresh every 30 seconds
**File:** `bot/services/cache_service.py`
```python
class BotCache:
    def register(self, key: str, path: str, ttl: float | None = None, force: bool = False) -> None:
        self._paths[key] = (path, ttl if ttl is not None else self.default_ttl, force)

    async def get(self, key: str, ..., force: bool = False):
        ...
        if force:
            sep = "&" if "?" in path else "?"
            path = f"{path}{sep}force=true"
        data = await api_client.get(path)

bot_cache.register("overview", "/api/seller/overview", ttl=30, force=True)
bot_cache.register("balance", "/api/seller/balance/full", ttl=30, force=True)
bot_cache.register("lots", "/api/seller/lots", ttl=30, force=True)
```

### 7.5 Fixed timezone to MSK
**File:** `bot/formatters.py`
```python
from datetime import timezone, timedelta
MSK = timezone(timedelta(hours=3))

def _ts(ts_val: float | None = None) -> str:
    if ts_val:
        dt = datetime.datetime.fromtimestamp(ts_val, tz=MSK)
    else:
        dt = datetime.datetime.now(MSK)
    return dt.strftime("%d.%m.%Y %H:%M")
```
**File:** `plugins/telegram_notifier_plugin.py`
```python
updated_str = datetime.fromtimestamp(updated, tz=timezone.utc).astimezone(MSK).strftime("%d.%m.%Y %H:%M") if updated else "—"
```

### 7.6 Fixed logs API
**File:** `web/logs_api.py`
- Removed demo log seeding
- Added real `logs/app.log` reading:
```python
def _read_app_log(limit=200, level=None, source=None, search=None):
    log_path = os.path.join(root, "logs", "app.log")
    ...
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
```

### Results
- Bot UI no longer has duplicate text
- Plugin buttons work correctly
- CPU/RAM displayed in health check
- Bot auto-refreshes data every 30 seconds
- All timestamps displayed in MSK (UTC+3)
- Logs show real application output, not demo data

### Commits
- `e5f6b63` - fix(bot): duplicate menu text, plugin callbacks, cpu/ram in health, real logs
- `a8e3113` - fix(bot): force refresh cached endpoints every 30s
- `eb8c491` - fix(bot): display all timestamps in MSK timezone

---

## 8. Deployment Status

### Current Status
- **Hub:** https://funpayhub.onrender.com/health → `ok`
- **Bot Worker:** https://funpayhub-tg-bot.onrender.com/health → `ok`
- **Bot:** @FunPayHubControl_bot (id=8811804174) — online

### Recent Commits
```
eb8c491 fix(bot): display all timestamps in MSK timezone
a8e3113 fix(bot): force refresh cached endpoints every 30s
e5f6b63 fix(bot): duplicate menu text, plugin callbacks, cpu/ram in health, real logs
b533697 fix(reports): exclude simulation/test data from reports
56662f2 docs(audit): add report system data sources fix section
95d7acc docs(audit): complete report system audit with full details
```

---

## 9. Pending Verification

1. **Production DB audit** — verify `source='real'` distribution on Render:
   ```sql
   SELECT source, COUNT(*) FROM orders GROUP BY source;
   SELECT id, funpay_order_id, source FROM orders WHERE source='real' LIMIT 20;
   ```

2. **Bot auto-start** — if `funpayhub-tg-bot` doesn't start automatically, check Render service status and logs for 502/504 errors.

3. **AI Agent analysis** — button works correctly, shows static TODO/FIXME/BUG markers. For fresh analysis use `/analyze path/to/file.py`.

---

# 1. Project tree

```
FunPayAPI/
FunPayAPI\common/
bot/
bot\handlers/
bot\keyboards/
bot\middlewares/
bot\services/
plugins/
plugins\execution/
runtime/
runtime\ai_team/
runtime\automation/
runtime\backup/
runtime\cache/
runtime\database/
runtime\export/
runtime\migrations/
runtime\migrations\versions/
runtime\notifications/
runtime\notifications\channels/
runtime\observability/
runtime\recovery/
runtime\state/
runtime\websocket/
scripts/
security/
tests/
web/
```

# 2. Entrypoints and startup chain

## funpayhub_main.py
- L1: `import sys`
- L1: `import os`
- L1: `import io`
- L2: `from datetime import datetime`
- L33: `import sys`
- L34: `import os`
- L35: `import threading`
- L36: `import time`
- L37: `import logging`
- L38: `import signal`
- L39: `from pathlib import Path`
- L82: `from flask import Flask`
- L83: `from web.plugin_management_api import plugin_mgmt_bp`
- L84: `from web.alerts_api import alerts_bp`
- L85: `from web.logs_api import logs_bp`

## hub_bootstrap.py
- L19: `from dotenv import load_dotenv`
- L23: `import os`
- L24: `import time`
- L25: `import json`
- L26: `import re`
- L27: `import threading`
- L28: `from typing import Any`
- L28: `from typing import List`
- L28: `from typing import Optional`
- L29: `import logging`
- L30: `from runtime.http_client import HTTPClient`
- L30: `from runtime.http_client import HTTPClientError`
- L31: `from security.secrets_manager import SecretsManager`
- L140: `import threading`
- L140: `import time`

## migrate_secrets.py
- L1: `import os`
- L2: `import configparser`
- L3: `from security.secrets_manager import SecretsManager`
- L73: `import json`

## run_bot.py
- L6: `import asyncio`
- L7: `import logging`
- L8: `import os`
- L9: `import sys`
- L11: `from dotenv import load_dotenv`
- L14: `from aiogram import Bot`
- L14: `from aiogram import Dispatcher`
- L15: `from aiogram.enums import ParseMode`
- L16: `from aiogram.client.default import DefaultBotProperties`
- L17: `from aiohttp import web`
- L19: `from bot.config import get_bot_config`
- L20: `from bot.middlewares import AuthMiddleware`
- L21: `from bot.handlers.start import router`
- L22: `from bot.handlers.callbacks import router`
- L23: `from bot.handlers.notifications import router`

## runtime\funpay_catalog.py
- L17: `from __future__ import annotations`
- L18: `import os`
- L18: `import re`
- L18: `import json`
- L18: `import time`
- L19: `from typing import List`
- L19: `from typing import Dict`
- L19: `from typing import Optional`
- L21: `from runtime.http_client import HTTPClient`
- L21: `from runtime.http_client import HTTPClientError`

## scripts\acceptance_test.py
- L5: `from __future__ import annotations`
- L7: `import argparse`
- L8: `import json`
- L9: `import os`
- L10: `import sys`
- L11: `import time`
- L12: `import threading`
- L13: `import traceback`
- L14: `import logging`
- L15: `import asyncio`
- L16: `from datetime import datetime`
- L16: `from datetime import timezone`
- L16: `from datetime import timedelta`
- L17: `from typing import Any`
- L17: `from typing import Dict`

## scripts\sim_audit.py
- L13: `from __future__ import annotations`
- L15: `import os`
- L16: `import sys`
- L17: `import time`
- L18: `import json`
- L19: `import asyncio`
- L20: `import threading`
- L21: `import traceback`
- L22: `from typing import Any`
- L22: `from typing import Dict`
- L22: `from typing import List`
- L22: `from typing import Optional`
- L115: `import runtime.seller_service`
- L120: `from flask import Flask`
- L120: `from flask import request`

## bot\keyboards\main.py
- L1: `from __future__ import annotations`
- L3: `from aiogram.types import InlineKeyboardMarkup`
- L3: `from aiogram.types import InlineKeyboardButton`

# 3. Global call graph (high-level)

- **FunPayAPI** → account, common
- **FunPayAPI.account** → FunPayAPI.common.enums, FunPayAPI.common.utils, __future__, bs4, common, datetime, html, json, logging, random, re, requests, requests.adapters, requests_toolbelt, string, time, types, typing, urllib3.util.retry
- **FunPayAPI.common.enums** → __future__, enum
- **FunPayAPI.common.exceptions** → requests
- **FunPayAPI.common.utils** → datetime, enums, random, re, string
- **FunPayAPI.types** → FunPayAPI.common.enums, __future__, common.enums, common.utils, datetime, re, typing
- **bot.api_client** → __future__, aiohttp, bot.config, json, logging, typing
- **bot.config** → __future__, dataclasses, json, os
- **bot.formatters** → __future__, datetime, html, typing
- **bot.handlers.ai_agent** → __future__, aiogram, aiogram.filters, aiogram.types, bot.services, logging
- **bot.handlers.callbacks** → __future__, aiogram, aiogram.exceptions, aiogram.types, bot.api_client, bot.config, bot.formatters, bot.keyboards.main, bot.services.cache_service, json, logging, os, psutil, subprocess, time, typing, urllib.parse
- **bot.handlers.notifications** → __future__, aiogram, aiogram.types, bot.formatters, bot.keyboards.main, logging
- **bot.handlers.start** → __future__, aiogram, aiogram.exceptions, aiogram.filters, aiogram.types, bcrypt, bot.config, bot.formatters, bot.keyboards.main, json, logging, os
- **bot.keyboards** → bot.keyboards.main
- **bot.keyboards.main** → __future__, aiogram.types
- **bot.middlewares** → bot.middlewares.auth
- **bot.middlewares.auth** → __future__, aiogram, aiogram.types, bcrypt, bot.config, json, logging, os, typing
- **bot.services** → bot.services.ai_agent_service
- **bot.services.ai_agent_service** → __future__, aiogram.types, aiohttp, asyncio, base64, dataclasses, datetime, json, logging, os, pathlib, time, typing
- **bot.services.cache_service** → __future__, asyncio, bot.api_client, logging, time, typing
- **eventbus** → collections, threading, typing
- **funpayhub_main** → datetime, flask, hub_bootstrap, io, logging, os, pathlib, runtime.http_client, signal, sys, threading, time, traceback, web.alerts_api, web.assistant_api, web.funpay_proxy, web.logs_api, web.plugin_management_api, web.seller_api, web.userdata_api, webbrowser, webview
- **hub_bootstrap** → dotenv, eventbus, json, logging, os, plugins.loader, plugins.plugin_manager, re, runtime.ai_engineer_agent, runtime.autoreply_engine, runtime.backup_manager, runtime.database.base, runtime.emergency_manager, runtime.http_client, runtime.notifications.notification_manager, runtime.order_flow, runtime.order_tracker, runtime.report_engine, runtime.runtime_controller, runtime.runtime_log, runtime.seller_service, runtime.supplier_worker, security.secrets_manager, shutil, threading, time, traceback, typing
- **migrate_secrets** → configparser, json, os, security.secrets_manager
- **plugins.autobump_plugin** → bot.config, collections, datetime, json, pathlib, plugins.plugin_base, runtime.http_client, threading, time
- **plugins.autodonate_plugin** → bot.config, pathlib, plugins.plugin_base, re, runtime.http_client, runtime.order_tracker, runtime.seller_service, threading, time
- **plugins.autosmm_plugin** → bot.config, collections, expiringdict, json, os, pathlib, plugins.plugin_base, re, runtime.autoreply_engine, runtime.http_client, runtime.lot_matcher, runtime.order_tracker, runtime.plugin_markers, runtime.seller_service, runtime.ttl_cache, sys, threading, time, urllib.parse
- **plugins.config_manager** → json, os, typing
- **plugins.dependency_manager** → collections, typing
- **plugins.execution** → plugins.execution.base, plugins.execution.executor_registry, plugins.execution.inprocess_executor, plugins.execution.process_manager, plugins.execution.subprocess_executor
- **plugins.execution.base** → abc
- **plugins.execution.executor_registry** → plugins.execution.base, plugins.execution.inprocess_executor, plugins.execution.subprocess_executor, typing
- **plugins.execution.inprocess_executor** → plugins.execution.base, time
- **plugins.execution.process_manager** → dataclasses, datetime, enum, threading, time, typing
- **plugins.execution.subprocess_executor** → multiprocessing, plugins.execution.base, plugins.execution.process_manager, plugins.execution.worker, threading, time
- **plugins.execution.worker** → importlib, plugins.plugin_base, sys, threading, time
- **plugins.health_score** → collections, time, typing
- **plugins.loader** → importlib, inspect, os, plugins.plugin_base, sys, typing
- **plugins.logger_plugin** → plugins.plugin_base
- **plugins.plugin_base** → plugins.config_manager, security.secrets_manager, typing
- **plugins.plugin_manager** → collections, plugins.dependency_manager, plugins.execution, plugins.health_score, plugins.plugin_base, plugins.plugin_registry, plugins.plugin_state, runtime.event_types, threading, time, typing
- **plugins.plugin_registry** → plugins.plugin_state, typing
- **plugins.plugin_state** → dataclasses, enum, typing
- **plugins.stars_plugin** → bot.config, json, os, pathlib, plugins.plugin_base, re, runtime.http_client, runtime.order_tracker, time, typing
- **plugins.telegram_notifier_plugin** → bot.config, json, os, plugins.plugin_base, runtime.http_client, threading, time, typing
- **run_bot** → aiogram, aiogram.client.default, aiogram.enums, aiohttp, asyncio, bot.config, bot.formatters, bot.handlers.ai_agent, bot.handlers.callbacks, bot.handlers.notifications, bot.handlers.start, bot.keyboards.main, bot.middlewares, bot.services, bot.services.cache_service, dotenv, logging, os, sys
- **runtime** → runtime.ai_team.ai_team_orchestrator, runtime.ai_team.model_manager, runtime.ai_team.scheduled_tasks, runtime.ai_team_orchestrator, runtime.event_types, runtime.observability.event_store, runtime.observability.health_engine, runtime.observability.metrics, runtime.observability.observability_hub, runtime.runtime_controller, runtime.runtime_log, runtime.websocket.websocket_hub
- **runtime.ai_engineer_agent** → datetime, json, logging, os, pathlib, re, runtime.http_client, threading, time, typing
- **runtime.ai_team** → runtime.ai_team.ai_team_orchestrator, runtime.ai_team.model_manager, runtime.ai_team.scheduled_tasks
- **runtime.ai_team.ai_team_orchestrator** → json, logging, re, runtime.ai_team.model_manager, threading, time, typing
- **runtime.ai_team.model_manager** → json, logging, pathlib, runtime.http_client, security.secrets_manager, time, typing
- **runtime.ai_team.scheduled_tasks** → datetime, logging, typing
- **runtime.ai_team_orchestrator** → datetime, json, os, pathlib, re, subprocess, time, typing
- **runtime.automation** → approval_manager, execution_history, patch_executor, patch_validator, rollback_manager, task_package
- **runtime.automation.approval_manager** → datetime, json, pathlib
- **runtime.automation.execution_history** → datetime, json, pathlib, typing
- **runtime.automation.patch_executor** → datetime, patch_validator, pathlib, shutil, task_package, tempfile, typing
- **runtime.automation.patch_validator** → pathlib, subprocess, sys, task_package, tempfile, typing
- **runtime.automation.rollback_manager** → pathlib, shutil, typing
- **runtime.automation.task_package** → dataclasses, datetime, json, typing
- **runtime.autoreply_engine** → bot.config, json, os, pathlib, runtime.http_client, runtime.plugin_markers, runtime.seller_service, sys, threading, time, typing
- **runtime.backup** → runtime.backup.backup_manager, runtime.backup.models, runtime.backup.restore_manager, runtime.backup.scheduler
- **runtime.backup.backup_manager** → datetime, hashlib, json, os, runtime.backup.models, shutil, typing, zipfile
- **runtime.backup.models** → dataclasses, datetime, typing
- **runtime.backup.restore_manager** → json, os, runtime.backup.models, shutil, tempfile, typing, zipfile
- **runtime.backup.scheduler** → runtime.backup.backup_manager, threading, time, typing
- **runtime.backup_manager** → datetime, logging, os, pathlib, shutil, threading, time, typing
- **runtime.cache.cache_manager** → __future__, threading, time
- **runtime.database** → runtime.database.base, runtime.database.ledger, runtime.database.models, runtime.database.repository
- **runtime.database.base** → os, pathlib, runtime.database.models, sqlalchemy, sqlalchemy.orm, threading
- **runtime.database.ledger** → decimal, runtime.database.base, runtime.database.models, sqlalchemy, time, typing
- **runtime.database.models** → enum, runtime.database.base, sqlalchemy, sqlalchemy.orm, time
- **runtime.database.repository** → runtime.database.base, runtime.database.models, sqlalchemy, time, typing
- **runtime.dependency_resolver** → dataclasses, typing
- **runtime.emergency_manager** → bot.config, logging, os, runtime.http_client, threading, time, typing
- **runtime.event_bus** → dataclasses, enum, time, uuid
- **runtime.event_types** → dataclasses, enum, time, uuid
- **runtime.export** → runtime.export.export_manager, runtime.export.import_manager, runtime.export.models, runtime.export.schema, runtime.export.validators
- **runtime.export.export_manager** → json, runtime.export.models, runtime.export.schema, typing
- **runtime.export.import_manager** → json, runtime.export.schema, runtime.export.validators, typing
- **runtime.export.models** → dataclasses, datetime, typing
- **runtime.export.schema** → datetime, json, runtime.export.models, typing
- **runtime.export.validators** → runtime.export.models, typing
- **runtime.funpay_catalog** → __future__, json, os, re, runtime.http_client, time, typing
- **runtime.http_client** → logging, random, requests, requests.adapters, time, typing, urllib3.util.retry
- **runtime.lot_generator** → itertools, json, logging, os, pathlib, random, runtime.database.base, runtime.database.models, typing
- **runtime.lot_matcher** → __future__, difflib, re, typing
- **runtime.migrations** → runtime.migrations.migration_base, runtime.migrations.migration_manager, runtime.migrations.migration_registry
- **runtime.migrations.base** → abc, typing
- **runtime.migrations.export_migrations** → runtime.migrations.migration_base, runtime.migrations.migration_registry, typing
- **runtime.migrations.migration_base** → abc, typing
- **runtime.migrations.migration_manager** → runtime.migrations.migration_registry, typing
- **runtime.migrations.migration_registry** → runtime.migrations.migration_base, typing
- **runtime.migrations.registry** → runtime.migrations.base, typing
- **runtime.migrations.versions.v1_to_v2_example** → runtime.migrations.base, runtime.migrations.registry, typing
- **runtime.notification_manager** → logging, os, runtime.http_client, typing
- **runtime.notifications** → runtime.notifications.channels.dashboard_channel, runtime.notifications.channels.discord_channel, runtime.notifications.channels.log_channel, runtime.notifications.notification_manager, runtime.notifications.notification_types
- **runtime.notifications.channels.base_channel** → runtime.notifications.notification_types
- **runtime.notifications.channels.dashboard_channel** → json, runtime.notifications.channels.base_channel, runtime.notifications.notification_types
- **runtime.notifications.channels.discord_channel** → datetime, runtime.http_client, runtime.notifications.channels.base_channel, runtime.notifications.notification_types
- **runtime.notifications.channels.log_channel** → runtime.notifications.channels.base_channel, runtime.notifications.notification_types
- **runtime.notifications.notification_manager** → runtime.notifications.notification_queue, runtime.notifications.notification_rules, runtime.notifications.notification_types, runtime.notifications.rate_limiter
- **runtime.notifications.notification_queue** → collections, threading, typing
- **runtime.notifications.notification_rules** → runtime.notifications.notification_types, time
- **runtime.notifications.notification_types** → dataclasses, enum, time, uuid
- **runtime.notifications.rate_limiter** → collections, time, typing
- **runtime.observability.event_store** → collections, runtime.event_types, typing
- **runtime.observability.health_engine** → runtime.observability.event_store, runtime.observability.metrics
- **runtime.observability.metrics** → collections, time, typing
- **runtime.observability.observability_hub** → eventbus, runtime.event_types, runtime.observability.event_store, runtime.observability.health_engine, runtime.observability.metrics
- **runtime.observability.resource_monitor** → psutil, threading, time, typing
- **runtime.order_flow** → bot.config, logging, pathlib, runtime.database.base, runtime.database.models, runtime.database.repository, runtime.http_client, runtime.plugin_markers, threading, time, typing
- **runtime.order_tracker** → json, os, pathlib, runtime.database.repository, runtime.http_client, sys, threading, time, typing
- **runtime.plugin_config_manager** → json, os, pathlib, typing
- **runtime.plugin_markers** → re, typing
- **runtime.price_monitor** → pathlib, time
- **runtime.recovery** → runtime.recovery.boot_journal, runtime.recovery.recovery_manager, runtime.recovery.report
- **runtime.recovery.boot_journal** → json, os, time, typing
- **runtime.recovery.recovery_manager** → runtime.recovery.boot_journal, runtime.recovery.report, runtime.state.migrations, runtime.state.snapshot_engine, runtime.state.storage, time, typing
- **runtime.recovery.report** → json, os, time, typing
- **runtime.report_engine** → datetime, json, logging, os, runtime.database.base, runtime.database.ledger, runtime.database.models, runtime.database.repository, runtime.http_client, sqlalchemy, threading, time, typing
- **runtime.runtime_controller** → eventbus, plugins.plugin_manager, runtime.event_types, runtime.runtime_log, time, typing, uuid
- **runtime.runtime_log** → collections, enum, time, typing
- **runtime.seller_service** → FunPayAPI, FunPayAPI.account, FunPayAPI.common.enums, concurrent.futures, dotenv, io, json, logging, os, pathlib, re, runtime.lot_matcher, sys, threading, time, traceback, typing, uuid, zipfile
- **runtime.simulator** → __future__, typing
- **runtime.snapshot_builder** → dashboard, runtime.context
- **runtime.state** → runtime.state.migrations, runtime.state.snapshot_engine, runtime.state.state_manager, runtime.state.storage
- **runtime.state.migrations** → typing
- **runtime.state.snapshot_engine** → time, typing
- **runtime.state.state_manager** → runtime.state.migrations, runtime.state.snapshot_engine, runtime.state.storage, threading, time, typing
- **runtime.state.storage** → json, os, tempfile, typing
- **runtime.supplier_registry** → json, os, runtime.http_client, typing
- **runtime.supplier_worker** → logging, queue, threading, time, typing
- **runtime.ttl_cache** → collections, threading, time
- **runtime.websocket.connection_manager** → threading, typing
- **runtime.websocket.event_serializer** → json, runtime.event_types
- **runtime.websocket.websocket_hub** → json, runtime.event_types, runtime.websocket.connection_manager, runtime.websocket.event_serializer
- **scripts.acceptance_test** → __future__, argparse, asyncio, bot.formatters, bot.handlers, bot.keyboards.main, bot.services.ai_agent_service, bot.services.cache_service, datetime, eventbus, flask, json, logging, os, pathlib, runtime.database.repository, runtime.emergency_manager, runtime.order_flow, runtime.report_engine, runtime.seller_service, runtime.simulator, signal, sys, threading, time, traceback, typing, urllib.error, urllib.request, web.logs_api, web.seller_api
- **scripts.run_simulation** → dotenv, funpayhub_main, json, os, pathlib, runtime.database.base, runtime.database.ledger, runtime.database.models, runtime.database.repository, sys, threading, time
- **scripts.sim_audit** → __future__, asyncio, bot.services.ai_agent_service, bot.services.cache_service, eventbus, flask, json, os, runtime.emergency_manager, runtime.order_flow, runtime.report_engine, runtime.seller_service, runtime.simulator, sys, threading, time, traceback, typing, urllib.error, urllib.request, web.seller_api
- **security.secrets_manager** → cryptography.fernet, json, logging, os, pathlib, re, sys, typing
- **state_api** → copy, time, typing
- **test_real_lot** → json, os, pathlib, subprocess, sys, time, urllib.error, urllib.request
- **tests.conftest** → dotenv, os, pytest
- **tests.test_ai_team_integration** → json, pytest, runtime.ai_team.ai_team_orchestrator, runtime.ai_team.model_manager, runtime.ai_team.scheduled_tasks, unittest.mock
- **tests.test_golden_key** → os
- **tests.test_telegram_panel_contracts** → ast, bot.formatters, pathlib, runtime.simulator
- **web.alerts_api** → flask, os, runtime.notifications.notification_manager, runtime.notifications.notification_types, sys
- **web.assistant_api** → bot.config, flask, json, pathlib, runtime.http_client, security.secrets_manager, sys, time, uuid
- **web.funpay_proxy** → bot.config, flask, re, runtime.http_client, runtime.seller_service, time
- **web.logs_api** → flask, json, os, runtime.runtime_log, sys, time
- **web.plugin_management_api** → datetime, flask, json, os, pathlib, runtime.dependency_resolver, runtime.plugin_config_manager, sys, traceback
- **web.seller_api** → flask, json, os, plugins.autodonate_plugin, plugins.autosmm_plugin, plugins.plugin_manager, random, re, runtime.lot_generator, runtime.seller_service, runtime.simulator, runtime.supplier_registry, sys, threading, time, traceback, uuid
- **web.userdata_api** → flask, hashlib, os, pathlib, sys, uuid

# 5. Audit: Report System Data Sources Fix (2026-07-13)

## Problem
Вечерний отчёт в 21:00 показывал абсурдные цифры:
- **Заказов: 11106** при доходе **150 ₽** (средняя цена заказа: 0.013 ₽)
- Это означало, что в отчёт включались тестовые заказы из Acceptance Test, simulation и FakeSeller

## Solution

### 1. Добавлено поле `source` в модель `Order` (runtime/database/models.py:L168)
```python
source = Column(String(32), default="real", nullable=False, index=True)
```
**Зачем:** разделить реальные заказы от тестовых. Возможные значения: `real`, `simulation`, `acceptance_test`.

### 2. Обновлён `Repository.create_order()` (runtime/database/repository.py:68)
```python
def create_order(..., source: str = "real") -> Order:
    ...
    order = Order(..., source=source)
```
**Зачем:** передавать источник при создании заказа.

### 3. Обновлена `get_balance_snapshot()` и `get_daily_report()` в Ledger (runtime/database/ledger.py)
- Добавлен параметр `real_only: bool = True`
- Запросы теперь JOIN с `orders` и фильтруют `source='real'`
**Зачем:** исключить из отчётов транзакции тестовых заказов.

### 4. Обновлен `Repository.get_dashboard_stats()` (runtime/database/repository.py:353)
- Фильтрует `source='real'` для всех статистик
**Зачем:** показывать только реальную статистику в панели управления.

### 5. Обновлен `LotGenerator._calculate_copies()` (runtime/lot_generator.py:41)
- Фильтрует по `Order.source == "real"`
**Зачем:** масштабирование лотов должно основываться только на реальных продажах.

### 6. Добавлена автоматическая миграция (runtime/database/base.py)
```python
def _migrate_add_order_source(engine):
    conn.execute("ALTER TABLE orders ADD COLUMN source VARCHAR(32) DEFAULT 'real' NOT NULL")
    _mark_existing_test_orders(conn)  # помечает sim_*, ORD*, db_stress_* как simulation
```
**Зачем:** добавить колонку в существующие БД и пометить старые тестовые заказы.

### 7. Обновлён `ReportEngine` (runtime/report_engine.py)
- `_build_daily_report()`: показывает источник каждого поля:
  ```
  📦 Заказов: 7
     Источник: orders.db WHERE source='real' AND started_at в периоде
  💰 Доход: 150.00 ₽
     Источник: transactions WHERE type='funpay_income' + JOIN orders(source='real')
  ```
- `_build_forecast()`: фильтрует по `source='real'` с источниками
**Зачем:** админ видит, откуда берутся цифры, и может доверять отчёту.

### 8. Обновлен `OrderFlowManager._db_create_order()` (runtime/order_flow.py)
```python
source = "simulation" if os.environ.get("FUNPAYHUB_SIMULATION") == "1" else "real"
Repository.create_order(..., source=source)
```
**Зачем:** автоматическое определение источника через env-переменную.

### 9. Обновлён `OrderPaymentTracker._on_new_order()` (runtime/order_tracker.py)
- Аналогичная логика определения `source`
**Зачем:** отслеживание платежей тоже должно учитывать источник.

### 10. Обновлены тестовые скрипты
- `scripts/run_simulation.py`: `source="simulation"`
- `scripts/acceptance_test.py`: `source="acceptance_test"`
**Зачем:** явно помечать тестовые заказы.

### 11. Восстановлен `SupplierOrderRegistry` (runtime/order_tracker.py)
- Статический класс для idempotency заказов
- Сохраняет `funpay_order_id -> supplier, supplier_order_id`
**Зачем:** предотвращает повторную отправку заказов поставщикам.

## Результат
- **Вечерний отчёт 21:00:** показывает только реальные заказы (например: 7 заказов, 150 ₽ доход)
- **Утренний отчёт 06:00:** фильтрует по `source='real'`
- **Панель управления:** показывает актуальные статистики
- **Масштабирование лотов:** основывается на реальных продажах
- **Прогнозы:** строятся только по реальным данным

## Проверки
- `pytest tests/`: 9/9 PASS
- Ручной тест: `get_daily_report(..., real_only=True)` видит только реальные данные
- Все модули импортируются без ошибок
- Репорт архитектура: [Аудит](#5-audit-report-system-data-sources-fix-2026-07-13)

## Изменённые файлы
1. `runtime/database/models.py` — добавлено поле `source`
2. `runtime/database/repository.py` — обновлён `create_order()`, `get_dashboard_stats()`, `count_orders()`
3. `runtime/database/ledger.py` — `get_balance_snapshot()`, `get_daily_report()`
4. `runtime/database/base.py` — миграция для `source` колонки
5. `runtime/report_engine.py` — аннотации источников, фильтрация
6. `runtime/order_flow.py` — определение `source` через env
7. `runtime/order_tracker.py` — определение `source`, восстановлен `SupplierOrderRegistry`
8. `runtime/lot_generator.py` — фильтрация продаж
9. `scripts/run_simulation.py` — передача `source="simulation"`

## Коммит и деплой
- **Коммит:** `b533697` - `fix(reports): exclude simulation/test data from reports; add source tracking`
- **Деплой:** Push в `origin/main` — Render автоматически пересобирает и деплоит
- **Проверка деплоя:** `https://funpayhub.onrender.com/health` → `ok`

# 4. Per-module audit

## `eventbus.py`

I:L2:import threading; L3:from typing import Dict; L3:from typing import List; L3:from typing import Callable; L3:from typing import Any; L4:from collections import defaultdict
C:L7:class EventBus[L10:__init__,L14:subscribe,L19:unsubscribe,L24:emit,L36:publish]
F:L10:def __init__()->['defaultdict', 'threading.Lock']; L14:def subscribe()->['self._listeners[event_type].append']; L19:def unsubscribe()->['self._listeners[event_type].remove']; L24:def emit()->['handler', 'print', 'self._listeners.get', 'self._listeners.get(event_type, []).copy']; L36:def publish()->['self.emit']
N:-

## `funpayhub_main.py`

I:L1:import sys; L1:import os; L1:import io; L2:from datetime import datetime; L33:import sys; L34:import os; L35:import threading; L36:import time; L37:import logging; L38:import signal; L39:from pathlib import Path; L82:from flask import Flask; L83:from web.plugin_management_api import plugin_mgmt_bp; L84:from web.alerts_api import alerts_bp; L85:from web.logs_api import logs_bp; L86:from web.seller_api import seller_bp; L87:from web.userdata_api import userdata_bp; L88:from web.funpay_proxy import funpay_proxy_bp; L89:from web.assistant_api import assistant_bp; L107:from hub_bootstrap import init_plugin_system
C:L12:class _Tee[L13:__init__,L15:write,L22:flush,L26:isatty]
F:L131:def _health()->['app.route']; L135:def _api_version()->['app.route']; L154:def _require_api_token()->['_req.headers.get', 'logger.warning', 'logging.getLogger', 'path.startswith']; L186:def _is_headless()->['os.environ.get', "os.environ.get('FUNPAYHUB_HEADLESS', '').strip", 'sys.platform.startswith']; L207:def _handle_sigterm()->['_shutdown_event.set', 'print']; L214:def run_flask()->['app.run']; L217:def main()->['HTTPClient', '_probe_client.get', '_shutdown_event.is_set', '_shutdown_event.wait']; L13:def __init__()->[] (+3 more)
N:L8:open; L9:file_write; L15:file_write; L18:file_write; L268:open

## `hub_bootstrap.py`

I:L19:from dotenv import load_dotenv; L23:import os; L24:import time; L25:import json; L26:import re; L27:import threading; L28:from typing import Any; L28:from typing import List; L28:from typing import Optional; L29:import logging; L30:from runtime.http_client import HTTPClient; L30:from runtime.http_client import HTTPClientError; L31:from security.secrets_manager import SecretsManager; L140:import threading; L140:import time; L140:import traceback; L430:import threading; L430:import time; L461:import threading; L461:import time
C:L44:class HubStateAPI[L48:__init__,L55:_fetch,L71:get_state,L82:get_balance,L90:get_withdrawable,L93:get_lots]
F:L139:def _start_background_worker()->['isinstance', 'print', 'result.get', 'seller_service.collect_account_notifications']; L165:def init_plugin_system()->['AIEngineerAgent', 'AutoReplyEngine', 'BackupManager', 'EmergencyManager']; L429:def _start_market_auto_update()->['_do_market_update', 'print', 't.start', 'threading.Thread']; L447:def _do_market_update()->['_http_client.get', '_http_client.post', 'print']; L460:def _start_auto_backup()->['_do_auto_backup', 'print', 't.start', 'threading.Thread']; L476:def _do_auto_backup()->['fname.endswith', 'os.listdir', 'os.makedirs', 'os.path.abspath']; L502:def _notify_telegram()->['_http_client.post', 'json.load', 'open', 'os.path.abspath']; L526:def _start_health_check()->['_run_health_check', 'logger.error', 'logger.info', 'logging.getLogger'] (+21 more)
N:L512:open

## `migrate_secrets.py`

I:L1:import os; L2:import configparser; L3:from security.secrets_manager import SecretsManager; L73:import json
C:-
F:L5:def migrate_config_file()->['config.read', 'config.write', 'configparser.ConfigParser', 'old_key.startswith']; L29:def main()->['SecretsManager', 'encryption_key.decode', 'json.dump', 'json.load']
N:L26:open; L27:file_write; L53:open; L59:open

## `run_bot.py`

I:L6:import asyncio; L7:import logging; L8:import os; L9:import sys; L11:from dotenv import load_dotenv; L14:from aiogram import Bot; L14:from aiogram import Dispatcher; L15:from aiogram.enums import ParseMode; L16:from aiogram.client.default import DefaultBotProperties; L17:from aiohttp import web; L19:from bot.config import get_bot_config; L20:from bot.middlewares import AuthMiddleware; L21:from bot.handlers.start import router; L22:from bot.handlers.callbacks import router; L23:from bot.handlers.notifications import router; L24:from bot.handlers.ai_agent import router; L25:from bot.keyboards.main import get_main_menu; L26:from bot.formatters import format_welcome; L27:from bot.services import ai_agent_service; L28:from bot.services.cache_service import bot_cache
C:-
F:L37:def _start_health_server()->['app.router.add_get', 'int', 'logger.info', 'os.environ.get']; L62:def main()->['AuthMiddleware', 'Bot', 'DefaultBotProperties', 'Dispatcher']; L48:def health()->['web.json_response']
N:L115:asyncio; L157:asyncio

## `state_api.py`

I:L7:import time; L8:from typing import Any; L8:from typing import Dict; L8:from typing import List; L8:from typing import Optional; L9:from copy import deepcopy
C:L11:class StateAPI[L18:__init__,L21:_get_state,L24:_get_lock,L27:get_state,L31:get_field,L35:get_balance]
F:L18:def __init__()->[]; L21:def _get_state()->['self._cardinal.get_state']; L24:def _get_lock()->[]; L27:def get_state()->['deepcopy', 'self._get_lock', 'self._get_state']; L31:def get_field()->['deepcopy', 'self._get_lock', 'self._get_state', 'self._get_state().get']; L35:def get_balance()->['float', 'self._get_lock', 'self._get_state', 'self._get_state().get']; L39:def get_withdrawable()->['float', 'self._get_lock', 'self._get_state', 'self._get_state().get']; L43:def get_lots()->['deepcopy', 'self._get_lock', 'self._get_state', 'self._get_state().get'] (+10 more)
N:-

## `test_real_lot.py`

I:L1:import os; L2:import sys; L3:import json; L4:import subprocess; L5:import time; L6:import urllib.request; L7:import urllib.error; L8:from pathlib import Path
C:-
F:-
N:L30:open; L30:subprocess; L45:urllib; L46:urllib; L46:open; L59:urllib

## `bot\api_client.py`

I:L1:from __future__ import annotations; L3:import json; L4:import logging; L5:from typing import Any; L7:import aiohttp; L9:from bot.config import get_bot_config
C:L14:class APIClientError(Exception)[]; L18:class APIClient[L19:__init__,L26:_request,L48:get,L51:post]
F:L19:def __init__()->['get_bot_config', 'self._cfg.hub_url.rstrip']; L26:def _request()->['APIClientError', '__import__', "__import__('os').environ.get", 'aiohttp.ClientSession']; L48:def get()->['self._request']; L51:def post()->['self._request']
N:L30:aiohttp; L32:aiohttp; L38:aiohttp

## `bot\config.py`

I:L1:from __future__ import annotations; L3:import os; L4:from dataclasses import dataclass; L30:import json
C:L8:class BotConfig[]
F:L15:def get_bot_config()->['BotConfig', 'RuntimeError', 'cfg.get', "cfg.get('bot_token', '').strip"]; L52:def get_hub_url()->['os.environ.get', 'render_url.strip', 'url.strip']
N:L29:open

## `bot\formatters.py`

I:L1:from __future__ import annotations; L3:import datetime; L4:from html import escape; L5:from typing import Any
C:-
F:L8:def _text()->['escape', 'str']; L14:def _ts()->['datetime.datetime.fromtimestamp', 'datetime.datetime.now', 'dt.strftime']; L22:def _safe_float()->['float']; L29:def format_welcome()->["'\\n'.join"]; L44:def format_balance()->["'\\n'.join", '_safe_float', '_text', '_ts']; L91:def format_report()->["'\\n'.join", '_text', '_ts', 'data.get']; L131:def format_system_status()->["'\\n'.join", '_text', '_ts', 'health_data.get']; L180:def format_lots()->["'\\n'.join", '_safe_float', '_text', 'data.get'] (+17 more)
N:-

## `bot\__init__.py`

I:
C:-
F:-
N:-

## `FunPayAPI\account.py`

I:L1:from __future__ import annotations; L3:import html; L4:from typing import TYPE_CHECKING; L4:from typing import Literal; L4:from typing import Any; L4:from typing import Optional; L4:from typing import IO; L6:import FunPayAPI.common.enums; L7:from FunPayAPI.common.utils import parse_currency; L7:from FunPayAPI.common.utils import RegularExpressions; L8:from types import PaymentMethod; L8:from types import CalcResult; L13:from requests_toolbelt import MultipartEncoder; L14:from bs4 import BeautifulSoup; L15:from datetime import datetime; L15:from datetime import timedelta; L16:import requests; L17:import logging; L18:import random; L19:import string
C:L33:class Account[L53:__init__,L145:method,L233:get,L284:runner_request,L306:get_payload_data,L353:abuse_runner]
F:L53:def __init__()->['HTTPAdapter', 'Retry', 'requests.Session', 'self.session.mount']; L145:def method()->['exceptions.RequestFailedError', 'exceptions.UnauthorizedError', 'link.endswith', 'min']; L233:def get()->['BeautifulSoup', 'balance.replace', 'balance.text.rsplit', 'cookies.get']; L284:def runner_request()->['json.dumps', 'payload.get', 'self.method']; L306:def get_payload_data()->['msg_ids.get', 'objects.append', 'objects.extend', 'sorted']; L353:def abuse_runner()->['self.get_payload_data', 'self.runner.get_result', 'self.runner_request']; L388:def get_subcategory_public_lots()->["''.join", 'BeautifulSoup', 'amount.isdigit', 'attributes.get']; L482:def get_my_subcategory_lots()->['BeautifulSoup', 'amount.isdigit', 'bool', 'exceptions.AccountNotInitiatedError'] (+60 more)
N:L773:open

## `FunPayAPI\types.py`

I:L4:from __future__ import annotations; L6:import re; L7:from typing import Literal; L7:from typing import overload; L7:from typing import Optional; L9:import FunPayAPI.common.enums; L10:from common.utils import RegularExpressions; L11:from common.enums import MessageTypes; L11:from common.enums import OrderStatuses; L11:from common.enums import SubCategoryTypes; L11:from common.enums import Currency; L12:import datetime
C:L15:class BaseOrderInfo[L20:__init__]; L29:class ChatShortcut(BaseOrderInfo)[L52:__init__,L76:get_last_message_type,L123:__str__]; L127:class BuyerViewing[L132:__init__,L148:lot_id,L156:subcategory_type]; L165:class Chat[L188:__init__]; L204:class Message(BaseOrderInfo)[L236:__init__,L293:get_message_type,L342:__str__]; L346:class OrderShortcut(BaseOrderInfo)[L390:__init__,L422:parse_amount,L435:__str__]; L438:class Server[L439:__init__]; L443:class Side[L444:__init__]; L448:class Order[L506:__init__,L550:get_field,L562:get_field_value,L582:get_field_value_any,L601:short_description,L605:title]; L665:class Category[L679:__init__,L695:add_subcategory,L706:get_subcategory,L721:get_subcategories,L730:get_sorted_subcategories]; L740:class SubCategory[L757:__init__,L777:is_common,L781:is_lots,L785:is_currency,L789:is_chips,L793:ui_name]; L803:class LotField[L804:__init__]; L810:class LotFields[L833:__init__,L878:amount,L890:amount,L894:public_link,L899:private_link,L904:fields]; L972:class ChipOffer[L973:__init__,L983:key]; L988:class ChipFields[L989:__init__,L1005:fields,L1014:renew_fields,L1037:__parse_offers]; L1056:class LotPage[L1082:__init__,L1100:seller_url]; L1105:class SellerShortcut[L1110:__init__,L1126:link]; L1130:class LotShortcut[L1159:__init__]; L1199:class MyLotShortcut[L1228:__init__]; L1263:class UserProfile[L1286:__init__,L1308:get_lot,L1322:get_lots,L1332:get_sorted_lots,L1336:get_sorted_lots,L1340:get_sorted_lots]; L1410:class Review[L1448:__init__]; L1475:class Balance[L1495:__init__]; L1511:class PaymentMethod[L1514:__init__]; L1525:class CalcResult[L1528:__init__,L1546:get_coefficient,L1557:commission_coefficient,L1562:commission_percent]; L1566:class Wallet[L1569:__init__]
F:L20:def __init__()->[]; L52:def __init__()->['BaseOrderInfo.__init__', 'self.get_last_message_type']; L76:def get_last_message_type()->['RegularExpressions', 'res.DEAR_VENDORS.search', 'res.DISCORD.search', 'res.ORDER_ID.search']; L123:def __str__()->[]; L132:def __init__()->['bool']; L148:def lot_id()->['id_.isdigit', 'int', 'self.link.split']; L156:def subcategory_type()->[]; L188:def __init__()->[] (+75 more)
N:-

## `FunPayAPI\__init__.py`

I:L1:from account import Account; L2:from common import exceptions; L2:from common import utils; L2:from common import enums; L3:from  import types
C:-
F:-
N:-

## `plugins\autobump_plugin.py`

I:L18:import time; L19:import threading; L20:import json; L21:from datetime import datetime; L21:from datetime import timedelta; L22:from collections import deque; L23:from pathlib import Path; L25:from plugins.plugin_base import PluginBase; L26:from runtime.http_client import HTTPClient; L26:from runtime.http_client import HTTPClientError; L129:from bot.config import get_hub_url; L344:import datetime
C:L42:class AutoBumpPlugin(PluginBase)[L126:__init__,L145:on_load,L149:on_enable,L158:on_disable,L164:on_unload,L167:on_error]
F:L367:def get_plugin_stats()->['hasattr', 'p.get_stats', 'plugin_manager.plugins.get']; L126:def __init__()->['HTTPClient', 'deque', 'get_hub_url', 'super']; L145:def on_load()->['json.dumps', 'self._log', 'self.load_config']; L149:def on_enable()->['self._log', 'self._stop_event.clear', 'self._thread.is_alive', 'self._thread.start']; L158:def on_disable()->['self._log', 'self._stop_event.set', 'self._thread.is_alive', 'self._thread.join']; L164:def on_unload()->['self.on_disable']; L167:def on_error()->['self._log']; L173:def _loop()->['int', 'max', 'range', 'self._log'] (+8 more)
N:-

## `plugins\autodonate_plugin.py`

I:L5:import time; L6:import re; L7:import threading; L8:from pathlib import Path; L9:from plugins.plugin_base import PluginBase; L10:from runtime.http_client import HTTPClient; L10:from runtime.http_client import HTTPClientError; L11:from runtime.order_tracker import get_supplier_order_registry; L128:from bot.config import get_hub_url; L499:from runtime.seller_service import seller_service_singleton
C:L89:class AutoDonatePlugin(PluginBase)[L125:__init__,L140:on_enable,L143:on_disable,L146:on_unload,L149:on_load,L164:on_event]
F:L125:def __init__()->['HTTPClient', 'get_hub_url', 'self._get_data_dir', 'super']; L140:def on_enable()->['self._start_replenish_timer']; L143:def on_disable()->['self._stop_replenish_timer']; L146:def on_unload()->['self._stop_replenish_timer']; L149:def on_load()->['env_mapping.items', 'self.config.get', "self.config.get('suppliers', {}).get", 'self.get_secret']; L164:def on_event()->['event.get', 'getattr', 'isinstance', 'self._on_new_message']; L183:def _on_new_order()->['DEFAULT_CONFIG.get', 'auto_resp.get', "auto_resp.get('discord_boost_received', DEFAULT_CONFIG['auto_responses']['discord_boost_received']).format", "auto_resp.get('game_rental_received', DEFAULT_CONFIG['auto_responses']['game_rental_received']).format"]; L247:def _on_new_message()->['any', 'auto_resp.get', 'event.get', 'getattr'] (+29 more)
N:-

## `plugins\autosmm_plugin.py`

I:L5:import os; L6:import time; L7:import threading; L8:import json; L9:import re; L10:from collections import deque; L11:from pathlib import Path; L12:from urllib.parse import urlparse; L14:from plugins.plugin_base import PluginBase; L15:from runtime.http_client import HTTPClient; L15:from runtime.http_client import HTTPClientError; L16:from runtime.order_tracker import get_supplier_order_registry; L19:from runtime.ttl_cache import TTLSet; L24:from expiringdict import ExpiringDict; L30:from runtime.autoreply_engine import chat_lock_registry; L35:from runtime.plugin_markers import has_marker_for; L151:from bot.config import get_hub_url; L515:import time; L913:import re; L987:import sys
C:L89:class AutoSMMPlugin(PluginBase)[L148:__init__,L179:_get_chat_lock,L189:on_load,L197:on_enable,L207:on_disable,L214:on_unload]
F:L148:def __init__()->['ExpiringDict', 'HTTPClient', 'TTLSet', 'deque']; L179:def _get_chat_lock()->['threading.Lock']; L189:def on_load()->['self._log', 'self.config.get', 'self.get_secret', 'self.load_config']; L197:def on_enable()->['self._log', 'self._stop.clear', 'self._worker.is_alive', 'self._worker.start']; L207:def on_disable()->['self._log', 'self._save_active_orders', 'self._stop.set', 'self._worker.is_alive']; L214:def on_unload()->['self.on_disable']; L217:def on_error()->['self._log', 'str']; L225:def _loop()->['int', 'max', 'range', 'self._check_active_orders'] (+50 more)
N:L12:urllib; L879:open; L901:open

## `plugins\config_manager.py`

I:L2:import os; L3:import json; L4:from typing import Dict; L4:from typing import Any
C:-
F:L9:def get_config_path()->['os.makedirs', 'os.path.exists', 'os.path.join']; L15:def load_raw_config()->['get_config_path', 'json.load', 'open', 'os.path.exists']; L26:def create_default_config()->['get_config_path', 'json.dump', 'open', 'os.path.exists']; L41:def load_plugin_config()->['create_default_config', 'full_config.items', 'get_config_path', 'load_raw_config']; L52:def save_plugin_config()->['get_config_path', 'json.dump', 'open', 'print']
N:L19:open; L34:open; L60:open

## `plugins\dependency_manager.py`

I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Set; L2:from typing import Optional; L2:from typing import Tuple; L3:from collections import deque
C:L5:class DependencyError(Exception)[]; L8:class CircularDependencyError(DependencyError)[]; L11:class MissingDependencyError(DependencyError)[]; L14:class DependencyGraph[L15:__init__,L21:add_plugin,L36:remove_plugin,L54:validate_dependencies,L62:detect_circular,L85:topological_sort]
F:L15:def __init__()->[]; L21:def add_plugin()->['self.hard_reverse[dep].add', 'self.soft_reverse[opt].add', 'set']; L36:def remove_plugin()->['deps.discard', 'self.hard_reverse.values', 'self.hard_reverse[dep].discard', 'self.soft_reverse.values']; L54:def validate_dependencies()->['MissingDependencyError', 'missing.update', 'self.graph.items', 'set']; L62:def detect_circular()->['cycles.append', 'dfs', 'path.index', 'self.graph.get']; L85:def topological_sort()->['CircularDependencyError', 'deque', 'in_degree.items', 'len']; L103:def get_hard_dependents()->['self.hard_reverse.get', 'set']; L106:def get_soft_dependents()->['self.soft_reverse.get', 'set'] (+4 more)
N:-

## `plugins\health_score.py`

I:L2:import time; L3:from collections import deque; L4:from typing import Optional
C:L6:class PluginHealthScore[L7:__init__,L15:update_latency,L18:update_error,L21:update_restart,L24:update_event_count,L27:tick]
F:L7:def __init__()->['deque']; L15:def update_latency()->['self._latency_history.append']; L18:def update_error()->['self._error_history.append']; L21:def update_restart()->['self._restart_history.append']; L24:def update_event_count()->['self._event_history.append']; L27:def tick()->[]; L31:def calculate_score()->['int', 'len', 'max', 'min']
N:-

## `plugins\loader.py`

I:L2:import os; L3:import sys; L4:import importlib; L5:import inspect; L6:from typing import Dict; L8:from plugins.plugin_base import PluginBase
C:-
F:L10:def discover_plugins()->['filename.endswith', 'filename.startswith', 'os.listdir', 'os.path.exists']; L22:def load_plugin()->['importlib.import_module', 'inspect.getmembers', 'issubclass', 'plugin_manager.register']; L35:def load_plugins()->['discover_plugins', 'len', 'load_plugin', 'plugin_manager.finalize_registration']; L52:def reload_plugin_config()->['plugin_manager.reload_plugin_config', 'print']
N:-

## `plugins\logger_plugin.py`

I:L2:from plugins.plugin_base import PluginBase
C:L4:class LoggerPlugin(PluginBase)[L17:on_init,L20:on_load,L24:on_enable,L27:on_disable,L30:on_error,L33:on_unload]
F:L17:def on_init()->['print']; L20:def on_load()->['print', 'self.PLUGIN_INFO.get', 'self.load_config']; L24:def on_enable()->['print']; L27:def on_disable()->['print']; L30:def on_error()->['print']; L33:def on_unload()->['print']; L36:def on_event()->['len', 'print', 'self.config.get']
N:-

## `plugins\plugin_base.py`

I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Optional; L2:from typing import Any; L3:from plugins.config_manager import load_plugin_config; L3:from plugins.config_manager import save_plugin_config; L4:from security.secrets_manager import SecretsManager
C:L6:class PluginBase[L18:__init__,L27:get_info,L30:get_dependencies,L33:get_optional_dependencies,L36:on_load,L39:on_enable]
F:L18:def __init__()->['SecretsManager']; L27:def get_info()->['self.__class__.PLUGIN_INFO.copy']; L30:def get_dependencies()->['self.PLUGIN_INFO.get']; L33:def get_optional_dependencies()->['self.PLUGIN_INFO.get']; L36:def on_load()->[]; L39:def on_enable()->[]; L42:def on_disable()->[]; L45:def on_event()->[] (+15 more)
N:-

## `plugins\plugin_manager.py`

I:L2:import threading; L3:import time; L4:from typing import Dict; L4:from typing import Type; L4:from typing import List; L4:from typing import Optional; L5:from collections import deque; L7:from plugins.plugin_base import PluginBase; L8:from plugins.plugin_state import PluginState; L8:from plugins.plugin_state import PluginStateMachine; L8:from plugins.plugin_state import PluginErrorContext; L9:from plugins.plugin_registry import PluginRegistry; L10:from plugins.dependency_manager import DependencyGraph; L10:from plugins.dependency_manager import MissingDependencyError; L10:from plugins.dependency_manager import CircularDependencyError; L11:from plugins.health_score import PluginHealthScore; L12:from plugins.execution import get_executor_registry; L200:from runtime.event_types import Event; L200:from runtime.event_types import EventAction; L200:from runtime.event_types import EventResult
C:L14:class PluginManager[L15:__init__,L36:set_event_bus,L39:_get_fsm,L42:_transition,L83:register,L107:finalize_registration]
F:L15:def __init__()->['DependencyGraph', 'PluginRegistry', 'get_executor_registry', 'threading.Event']; L36:def set_event_bus()->[]; L39:def _get_fsm()->['self._fsm.get']; L42:def _transition()->['PluginErrorContext', 'error_context.to_string', 'fsm.apply_transition', 'fsm.can_transition']; L83:def register()->['PluginHealthScore', 'PluginStateMachine', 'callable', 'getattr']; L107:def finalize_registration()->['Exception', 'any', 'info.get', 'plugin.PLUGIN_INFO.get']; L138:def _start_watchdog()->['print', 'self._stop_watchdog.clear', 'self._watchdog_thread.is_alive', 'self._watchdog_thread.start']; L145:def _watchdog_loop()->['self._check_plugin_health', 'self._stop_watchdog.wait'] (+25 more)
N:L317:db

## `plugins\plugin_registry.py`

I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Optional; L3:from plugins.plugin_state import PluginState
C:L6:class PluginRegistry[L12:__init__,L17:register_metadata,L32:update_state,L44:get_plugin,L58:get_all_plugins,L61:get_plugins_count]
F:L12:def __init__()->[]; L17:def register_metadata()->['metadata.get', 'print']; L32:def update_state()->['print', 'self._errors.pop']; L44:def get_plugin()->['self._errors.get', 'self._states.get']; L58:def get_all_plugins()->['self._metadata.keys', 'self.get_plugin']; L61:def get_plugins_count()->['len']; L64:def get_plugin_state()->['self._states.get']; L67:def plugin_exists()->[]
N:-

## `plugins\plugin_state.py`

I:L2:from enum import Enum; L3:from typing import Dict; L3:from typing import Set; L3:from typing import Optional; L4:from dataclasses import dataclass
C:L7:class PluginState(Enum)[]; L27:class PluginErrorContext[L31:to_string]; L37:class PluginStateMachine[L38:__init__,L43:get_state,L46:get_state_name,L49:get_error_context,L52:get_error_message,L55:can_transition]
F:L31:def to_string()->[]; L38:def __init__()->[]; L43:def get_state()->[]; L46:def get_state_name()->[]; L49:def get_error_context()->[]; L52:def get_error_message()->['self._error_context.to_string']; L55:def can_transition()->['ALLOWED_TRANSITIONS.get', 'set']; L58:def apply_transition()->['print', 'self.can_transition']
N:-

## `plugins\stars_plugin.py`

I:L1:import os; L2:import re; L3:import time; L4:import json; L5:from pathlib import Path; L6:from typing import Optional; L6:from typing import Dict; L6:from typing import Any; L7:from plugins.plugin_base import PluginBase; L8:from runtime.http_client import HTTPClient; L8:from runtime.http_client import HTTPClientError; L9:from runtime.order_tracker import get_tracker; L48:from bot.config import get_hub_url
C:L28:class StarsPlugin(PluginBase)[L45:__init__,L53:on_load,L58:on_event,L69:_on_new_stars_order,L117:_create_stars_order,L157:_check_stars_status]
F:L45:def __init__()->['HTTPClient', 'get_hub_url', 'self._get_data_dir', 'super']; L53:def on_load()->['self._log', 'self.load_config']; L58:def on_event()->['event.get', 'getattr', 'isinstance', 'self._on_new_stars_order']; L69:def _on_new_stars_order()->["DEFAULT_CONFIG['msg_completed'].format", "DEFAULT_CONFIG['msg_error'].format", "DEFAULT_CONFIG['msg_order_created'].format", 'fragment_order.get']; L117:def _create_stars_order()->['ValueError', 'int', 'isinstance', 'response.get']; L157:def _check_stars_status()->['response.get', 'self.http_client.get']; L178:def _parse_stars()->['int', 'match.group', 're.search']; L185:def _get_buyer_username()->['buyer.strip', 'getattr', 'isinstance', 'order_data.get'] (+5 more)
N:-

## `plugins\telegram_notifier_plugin.py`

I:L5:import time; L6:import threading; L7:import json; L8:import os; L9:from typing import Any; L9:from typing import Optional; L9:from typing import Dict; L9:from typing import List; L10:from plugins.plugin_base import PluginBase; L11:from runtime.http_client import HTTPClient; L11:from runtime.http_client import HTTPClientError; L57:from bot.config import get_hub_url
C:L35:class TelegramNotifierPlugin(PluginBase)[L54:__init__,L65:on_load,L72:on_enable,L83:on_disable,L86:on_unload,L93:on_event]
F:L54:def __init__()->['HTTPClient', 'get_hub_url', 'super', 'super().__init__']; L65:def on_load()->['self.config.get', 'self.get_secret', "self.get_secret('TELEGRAM_NOTIFIER_BOT_TOKEN', '').strip", "self.get_secret('TELEGRAM_NOTIFIER_CHAT_ID', '').strip"]; L72:def on_enable()->['os.environ.get', "os.environ.get('TELEGRAM_BOT_TOKEN', '').strip", 'self._log', 'self._start_polling']; L83:def on_disable()->['self._stop_polling']; L86:def on_unload()->['self._stop_polling']; L93:def on_event()->['event.get', 'getattr', 'isinstance', 'self._send_telegram']; L124:def _send_telegram()->['data.get', 'int', 'json.dumps', 'self._log']; L154:def _answer_callback()->['self.config.get', "self.config.get('bot_token', '').strip", 'self.http_client.post'] (+18 more)
N:-

## `runtime\ai_engineer_agent.py`

I:L9:import os; L10:import re; L11:import time; L12:import json; L13:import threading; L14:import logging; L15:from pathlib import Path; L16:from typing import Optional; L16:from typing import List; L16:from typing import Dict; L16:from typing import Any; L17:from datetime import datetime; L17:from datetime import timezone; L17:from datetime import timedelta; L177:from runtime.http_client import HTTPClient
C:L22:class AIEngineerAgent[L32:__init__,L48:start,L55:stop,L62:_start_scanner,L73:_scan_logs,L97:_analyze_errors]
F:L32:def __init__()->['Path', 'os.environ.get', 'threading.Event']; L48:def start()->['logger.info', 'logger.warning', 'self._start_scanner']; L55:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L62:def _start_scanner()->['logger.error', 'self._scan_logs', 'self._stop.is_set', 'self._worker.start']; L73:def _scan_logs()->['any', 'errors.append', 'f.readlines', 'f.seek']; L97:def _analyze_errors()->["'\\n'.join", 'self._propose_patch', 'self._simple_fix_suggestion']; L106:def _simple_fix_suggestion()->['suggestions.items']; L137:def _propose_patch()->['int', 'self._pending_patches.append', 'self._send_admin', 'time.time'] (+3 more)
N:L78:open

## `runtime\ai_team_orchestrator.py`

I:L1:import json; L2:import os; L3:import re; L4:import subprocess; L5:import time; L6:from datetime import datetime; L7:from pathlib import Path; L8:from typing import Any; L8:from typing import Dict; L8:from typing import List; L8:from typing import Optional
C:L11:class LogMonitor[L12:__init__,L16:collect_errors,L26:_scan_file]; L44:class TaskManager[L45:__init__,L50:_load_tasks,L62:_save_tasks,L66:create_task,L85:_get_context]; L89:class AITeamOrchestrator[L90:__init__,L95:run_once,L108:_apply_safe_fix]
F:L12:def __init__()->['Path']; L16:def collect_errors()->['issues.extend', 'root.exists', 'root.is_dir', 'root.rglob']; L26:def _scan_file()->['any', 'enumerate', 'issues.append', 'line.strip']; L45:def __init__()->['Path', 'self.tasks_file.parent.mkdir']; L50:def _load_tasks()->['isinstance', 'json.load', 'open', 'self.tasks_file.exists']; L62:def _save_tasks()->['json.dump', 'open']; L66:def create_task()->['datetime.now', 'datetime.now().isoformat', 'datetime.now().timestamp', 'error_data.get']; L85:def _get_context()->[] (+3 more)
N:L29:open; L54:open; L63:open; L116:open; L117:file_write

## `runtime\autoreply_engine.py`

I:L7:import json; L8:import time; L9:import threading; L10:from pathlib import Path; L11:from typing import Optional; L14:from runtime.plugin_markers import has_any_marker; L20:import sys; L20:import os; L27:import os; L374:from runtime.plugin_markers import has_any_marker; L429:from runtime.plugin_markers import has_any_marker; L274:from runtime.http_client import HTTPClient; L275:from bot.config import get_hub_url; L244:from runtime.seller_service import seller_service_singleton; L254:from runtime.http_client import HTTPClient; L255:from bot.config import get_hub_url
C:L38:class ChatLockRegistry[L39:__init__,L43:acquire,L53:release,L64:is_locked,L77:owner]; L93:class AutoReplyEngine[L94:__init__,L102:_is_processed_by_autosmm,L110:subscribe,L119:_load_rules,L134:_load_templates,L160:_resolve_template]
F:L19:def _project_root()->['Path', 'Path(__file__).resolve', 'Path(sys.executable).resolve', 'getattr']; L26:def _configs_dir()->['Path', '_project_root', 'os.environ.get']; L39:def __init__()->['threading.RLock']; L43:def acquire()->['cur.get', 'self._locks.get', 'str', 'time.time']; L53:def release()->['cur.get', 'self._locks.get', 'self._locks.pop', 'str']; L64:def is_locked()->['cur.get', 'self._locks.get', 'self._locks.pop', 'str']; L77:def owner()->['cur.get', 'self._locks.get', 'str', 'time.time']; L94:def __init__()->['threading.RLock'] (+15 more)
N:-

## `runtime\backup_manager.py`

I:L9:import os; L10:import time; L11:import shutil; L12:import threading; L13:import logging; L14:from pathlib import Path; L15:from datetime import datetime; L16:from typing import Optional
C:L21:class BackupManager[L22:__init__,L35:start,L39:stop,L46:backup_now,L72:restore,L98:list_backups]
F:L22:def __init__()->['Path', 'Path(__file__).resolve', 'self._backup_dir.mkdir', 'threading.Event']; L35:def start()->['logger.info', 'self._start_daily_backup']; L39:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L46:def backup_now()->['datetime.now', 'datetime.now().strftime', 'logger.error', 'logger.info']; L72:def restore()->['Path', 'logger.error', 'logger.info', 'self._db_path.exists']; L98:def list_backups()->['self._backup_dir.exists', 'self._backup_dir.iterdir', 'sorted', 'str']; L109:def _start_daily_backup()->['datetime.now', 'datetime.now().strftime', 'logger.error', 'self._stop.is_set']; L110:def _loop()->['datetime.now', 'datetime.now().strftime', 'logger.error', 'self._stop.is_set']
N:-

## `runtime\context.py`

I:
C:L2:class AppContext[L3:__init__,L10:set_runtime_controller,L13:set_event_bus,L16:set_websocket_hub,L19:set_snapshot_builder,L22:update_snapshot]
F:L40:def get_app_context()->['AppContext']; L3:def __init__()->[]; L10:def set_runtime_controller()->[]; L13:def set_event_bus()->[]; L16:def set_websocket_hub()->[]; L19:def set_snapshot_builder()->[]; L22:def update_snapshot()->[]; L25:def get_snapshot()->[] (+3 more)
N:-

## `runtime\dependency_resolver.py`

I:L1:from typing import Dict; L1:from typing import List; L1:from typing import Set; L1:from typing import Optional; L2:from dataclasses import dataclass
C:L5:class PluginDependency[]; L10:class DependencyResolver[L11:__init__,L15:register_plugin,L27:get_dependencies,L34:get_dependents,L42:can_disable,L52:can_enable]
F:L11:def __init__()->[]; L15:def register_plugin()->['PluginDependency', 'dep.get']; L27:def get_dependencies()->[]; L34:def get_dependents()->['any', 'dependents.append', 'self.plugin_deps.items']; L42:def can_disable()->["', '.join", 'self.get_dependents']; L52:def can_enable()->["', '.join", 'missing_deps.append']; L67:def get_dependency_graph()->['self.plugin_deps.items']; L74:def get_load_order()->['order.append', 'self.plugin_deps.keys', 'set', 'visit'] (+1 more)
N:-

## `runtime\emergency_manager.py`

I:L18:import time; L19:import logging; L20:import threading; L21:from typing import Optional; L21:from typing import Set; L224:import os; L172:from runtime.http_client import HTTPClient; L173:from bot.config import get_hub_url; L184:from runtime.http_client import HTTPClient; L185:from bot.config import get_hub_url; L196:from runtime.http_client import HTTPClient; L197:from bot.config import get_hub_url; L210:from runtime.http_client import HTTPClient
C:L26:class EmergencyManager[L35:__init__,L63:state,L67:is_normal,L71:is_emergency,L74:start,L78:stop]
F:L35:def __init__()->['getattr', 'set', 'threading.RLock', 'time.time']; L63:def state()->[]; L67:def is_normal()->[]; L71:def is_emergency()->[]; L74:def start()->['logger.info']; L78:def stop()->['logger.info']; L83:def check_supplier()->['self._deactivate_supplier', 'self._error_counts.get', 'self._paused_suppliers.add', 'self._paused_suppliers.discard']; L112:def check_cancel_rate()->['max', 'self.emergency_stop'] (+9 more)
N:-

## `runtime\event_bus.py`

I:L2:import time; L3:import uuid; L4:from dataclasses import dataclass; L4:from dataclasses import field; L5:from enum import Enum
C:L8:class EventAction(Enum)[]; L19:class EventResult(Enum)[]; L26:class EventSource(Enum)[]; L33:class EventSeverity(Enum)[]; L40:class Event[L52:__post_init__,L61:to_dict]
F:L52:def __post_init__()->[]; L61:def to_dict()->[]
N:-

## `runtime\event_types.py`

I:L2:import time; L3:import uuid; L4:from dataclasses import dataclass; L4:from dataclasses import field; L5:from enum import Enum
C:L8:class EventAction(Enum)[]; L19:class EventResult(Enum)[]; L26:class EventSource(Enum)[]; L33:class EventSeverity(Enum)[]; L40:class Event[L52:__post_init__,L61:to_dict]
F:L52:def __post_init__()->[]; L61:def to_dict()->[]
N:-

## `runtime\funpay_catalog.py`

I:L17:from __future__ import annotations; L18:import os; L18:import re; L18:import json; L18:import time; L19:from typing import List; L19:from typing import Dict; L19:from typing import Optional; L21:from runtime.http_client import HTTPClient; L21:from runtime.http_client import HTTPClientError
C:-
F:L34:def _ensure_dir()->['os.makedirs']; L58:def fetch_all_subcategories()->['RE_GAME_BLOCK.findall', 'RE_GAME_TITLE.search', 'RE_SUB_LINK.finditer', '_ensure_dir']; L142:def get_cached()->['json.load', 'open', 'os.path.exists']
N:L71:open; L134:open; L146:open

## `runtime\http_client.py`

I:L14:import logging; L15:import random; L16:import time; L17:from typing import Any; L17:from typing import Dict; L17:from typing import Optional; L17:from typing import Union; L19:import requests; L20:from requests.adapters import HTTPAdapter; L21:from urllib3.util.retry import Retry
C:L38:class HTTPClientError(Exception)[L40:__init__,L50:_format]; L68:class HTTPClient[L83:__init__,L116:get,L120:post,L124:put,L128:delete,L136:_request]
F:L40:def __init__()->['self._format', 'super', 'super().__init__']; L50:def _format()->["' — '.join", 'parts.append']; L83:def __init__()->['HTTPAdapter', 'Retry', 'requests.Session', 'self._session.headers.update']; L116:def get()->['self._request']; L120:def post()->['self._request']; L124:def put()->['self._request']; L128:def delete()->['self._request']; L136:def _request()->['HTTPClientError', 'dict', 'kwargs.items', 'kwargs.pop'] (+5 more)
N:-

## `runtime\lot_generator.py`

I:L5:import os; L6:import json; L7:import random; L8:import itertools; L9:from pathlib import Path; L10:from typing import List; L10:from typing import Dict; L10:from typing import Any; L10:from typing import Optional; L11:import logging; L475:import os; L37:from runtime.database.base import get_session; L38:from runtime.database.models import Order
C:L15:class LotGenerator[L16:__init__,L32:_calculate_copies,L54:_calculate_market_price,L82:_load_return_policy,L91:_load_synonyms,L101:_load_emojis]
F:L16:def __init__()->['Path', 'self._load_emojis', 'self._load_return_policy', 'self._load_synonyms']; L32:def _calculate_copies()->['Order.status.in_', 'get_session', 'reversed', 'session.close']; L54:def _calculate_market_price()->['float', 'getattr', 'isinstance', 'l.get']; L82:def _load_return_policy()->['Path', 'policy_path.exists', 'policy_path.read_text', "policy_path.read_text(encoding='utf-8').strip"]; L91:def _load_synonyms()->['Path', 'data.get', 'isinstance', 'json.loads']; L101:def _load_emojis()->['Path', 'isinstance', 'json.loads', 'path.exists']; L111:def _load_twiboost_services()->['data.get', 'isinstance', 'json.loads', 'self._cache_path.exists']; L123:def _load_kosell_products()->[] (+10 more)
N:L41:db

## `runtime\lot_matcher.py`

I:L23:from __future__ import annotations; L24:import re; L25:from difflib import SequenceMatcher; L26:from typing import List; L26:from typing import Dict; L26:from typing import Optional
C:-
F:L33:def _normalize()->['re.sub', "re.sub('\\\\s+', ' ', t).strip", 'text.lower']; L42:def _extract_quantities()->["(m.group(2) or '').lower", '_QTY_RE.finditer', 'int', 'm.group']; L58:def _text_similarity()->['SequenceMatcher', 'SequenceMatcher(None, _normalize(a), _normalize(b)).ratio', '_normalize']; L64:def match_lot_to_service()->["(s.get('type') or '').lower", 'LOT_GROUPS.items', 'SERVICE_TYPE_MAP.get', '_extract_quantities']; L226:def classify_match()->[]; L234:def auto_build_mapping()->['len', 'lot.get', 'match_lot_to_service', 'out_skipped.append']
N:-

## `runtime\notification_manager.py`

I:L1:import os; L2:import logging; L3:from typing import Optional; L3:from typing import Dict; L4:from runtime.http_client import HTTPClient; L4:from runtime.http_client import HTTPClientError
C:L8:class NotificationManager[L15:__init__,L19:_log,L23:send_admin_notification,L43:send_user_notification,L58:send_discord_notification,L76:send_order_status_notification]
F:L15:def __init__()->['HTTPClient']; L19:def _log()->['getattr', 'level.lower']; L23:def send_admin_notification()->['self._log', 'self.http_client.post']; L43:def send_user_notification()->['self._log']; L58:def send_discord_notification()->['self._log', 'self.http_client.post']; L76:def send_order_status_notification()->['self.send_user_notification']; L92:def send_error_notification()->['self.send_admin_notification']
N:-

## `runtime\order_flow.py`

I:L18:import time; L19:import threading; L20:import logging; L21:from typing import Optional; L21:from typing import Dict; L21:from typing import Any; L22:from pathlib import Path; L166:from runtime.http_client import HTTPClient; L167:from bot.config import get_hub_url; L183:from runtime.http_client import HTTPClient; L184:from bot.config import get_hub_url; L460:from runtime.plugin_markers import parse_marker; L519:from runtime.http_client import HTTPClient; L535:from runtime.database.repository import Repository; L548:from runtime.database.repository import Repository; L555:from runtime.database.repository import Repository; L557:from runtime.database.base import get_session; L558:from runtime.database.models import Order
C:L27:class OrderFlowManager[L30:__init__,L48:start,L57:stop,L64:_on_new_order,L115:_on_order_cancelled,L136:_handle_low_balance]
F:L30:def __init__()->['threading.Event', 'threading.RLock']; L48:def start()->['logger.info', 'self._eb.subscribe', 'self._start_worker']; L57:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L64:def _on_new_order()->['event.get', 'getattr', 'isinstance', 'logger.error']; L115:def _on_order_cancelled()->['event.get', 'getattr', 'isinstance', 'logger.error']; L136:def _handle_low_balance()->['logger.warning', 'order.get', 'self._deactivate_supplier_lots', 'self._orders.get']; L157:def _check_supplier_balance()->['HTTPClient', 'data.get', 'entry.get', 'float']; L180:def _deactivate_supplier_lots()->['HTTPClient', 'get_hub_url', 'hc.post'] (+22 more)
N:L561:db

## `runtime\order_tracker.py`

I:L7:import json; L8:import time; L9:import threading; L10:from runtime.http_client import HTTPClient; L11:from pathlib import Path; L12:from typing import Optional; L12:from typing import Dict; L12:from typing import Any; L18:import sys; L18:import os; L160:from pathlib import Path; L315:from runtime.database.repository import Repository; L216:from runtime.database.repository import Repository
C:L34:class OrderPaymentTracker[L35:__init__,L45:start,L51:stop,L56:_start_worker,L84:_process_action,L122:_send_timeout_warning]; L262:class SupplierOrderRegistry[L270:__init__,L284:is_registered,L295:get_supplier_order_id,L303:register,L325:remove,L335:_load]
F:L17:def _project_root()->['Path', 'Path(__file__).resolve', 'Path(sys.executable).resolve', 'getattr']; L24:def _tg_config()->['_project_root', 'cfg_path.exists', 'cfg_path.read_text', 'json.loads']; L246:def get_tracker()->['OrderPaymentTracker', '_tracker_singleton.start']; L359:def get_supplier_order_registry()->['SupplierOrderRegistry']; L35:def __init__()->['_tg_config', '_tg_config().get', 'threading.Event', 'threading.RLock']; L45:def start()->['self._start_worker', 'self.event_bus.subscribe']; L51:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L56:def _start_worker()->['print', 'self._process_action', 'self._stop.is_set', 'self._worker.start'] (+16 more)
N:-

## `runtime\plugin_config_manager.py`

I:L1:import json; L2:import os; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Optional; L4:from pathlib import Path
C:L6:class PluginConfigManager[L7:__init__,L13:load_all_configs,L23:get_config,L27:update_config,L45:create_default_config,L55:validate_config]
F:L7:def __init__()->['Path', 'self.config_dir.mkdir', 'self.load_all_configs']; L13:def load_all_configs()->['json.load', 'open', 'print', 'self.config_dir.glob']; L23:def get_config()->['self.configs.get']; L27:def update_config()->['json.dump', 'json.dumps', 'open', 'print']; L45:def create_default_config()->['self.update_config']; L55:def validate_config()->['isinstance']
N:L18:open; L35:open

## `runtime\plugin_markers.py`

I:L23:import re; L24:from typing import Optional; L24:from typing import Tuple
C:-
F:L42:def parse_marker()->['_MARKER_RE.search', 'm.group']; L55:def parse_all_markers()->['_MARKER_RE.finditer', 'm.group']; L62:def has_any_marker()->['parse_marker']; L67:def has_marker_for()->['code.upper', 'parse_all_markers', 'plugin_code.upper']; L80:def strip_markers()->['_MARKER_RE.sub', "_MARKER_RE.sub('', text).strip"]; L87:def make_marker()->['plugin_code.upper']
N:-

## `runtime\price_monitor.py`

I:L4:import time; L5:from pathlib import Path
C:-
F:L7:def auto_adjust_prices()->['l.get', 'len', 'lot.get', 'my_lots.get']
N:-

## `runtime\report_engine.py`

I:L9:import time; L10:import threading; L11:import logging; L12:from datetime import datetime; L12:from datetime import timezone; L12:from datetime import timedelta; L13:from typing import Optional; L13:from typing import Dict; L13:from typing import Any; L99:from runtime.database.ledger import Ledger; L132:from runtime.database.repository import Repository; L133:from runtime.database.ledger import Ledger; L134:from runtime.database.base import get_session; L135:from runtime.database.models import Order; L135:from runtime.database.models import Provider; L136:from sqlalchemy import func; L212:from runtime.http_client import HTTPClient; L213:import os; L213:import json
C:L21:class ReportEngine[L24:__init__,L30:start,L35:stop,L42:_start_scheduler,L63:send_daily_report,L72:send_evening_summary]
F:L24:def __init__()->['threading.Event']; L30:def start()->['logger.info', 'self._start_scheduler']; L35:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L42:def _start_scheduler()->['datetime.now', 'logger.error', 'self._stop.is_set', 'self._worker.start']; L63:def send_daily_report()->['logger.info', 'self._build_daily_report', 'self._send_admin', 'time.time']; L72:def send_evening_summary()->['logger.info', 'self._build_daily_report', 'self._build_forecast', 'self._send_admin']; L88:def send_report_on_demand()->['self._build_daily_report', 'time.time']; L96:def _build_daily_report()->["'\\n'.join", 'Ledger.get_daily_report', 'abs', 'by_type.items'] (+4 more)
N:L150:db; L155:db; L157:db

## `runtime\runtime_controller.py`

I:L2:import time; L3:import uuid; L4:from typing import Dict; L4:from typing import List; L4:from typing import Optional; L4:from typing import Any; L5:from plugins.plugin_manager import PluginManager; L6:from runtime.runtime_log import RuntimeLog; L6:from runtime.runtime_log import LogLevel; L7:from eventbus import EventBus; L8:from runtime.event_types import Event; L8:from runtime.event_types import EventAction; L8:from runtime.event_types import EventResult; L8:from runtime.event_types import EventSource; L8:from runtime.event_types import EventSeverity
C:L11:class RuntimeController[L12:__init__,L24:set_observability_hub,L27:_emit_event,L45:_log_operation,L61:_get_health_status,L70:_get_plugins_list]
F:L12:def __init__()->['self._plugin_manager.set_event_bus', 'self._runtime_log.info']; L24:def set_observability_hub()->[]; L27:def _emit_event()->['Event', 'self._event_bus.emit', 'str', 'uuid.uuid4']; L45:def _log_operation()->['message.lower', 'self._runtime_log.add', 'self._runtime_log.info']; L61:def _get_health_status()->['self._plugin_manager.get_plugin_names', 'self._plugin_manager.get_plugin_state']; L70:def _get_plugins_list()->['info.get', 'plugin.get_info', 'plugins.append', 'self._plugin_manager.get_plugin_names']; L84:def _build_response()->['time.time']; L96:def enable_plugin()->['self._build_response', 'self._emit_event', 'self._log_operation', 'self._observability.record_plugin_uptime_start'] (+22 more)
N:-

## `runtime\runtime_log.py`

I:L2:import time; L3:from typing import List; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Optional; L4:from enum import Enum; L5:from collections import deque
C:L8:class LogLevel(Enum)[]; L15:class RuntimeLogEntry[L16:__init__,L23:to_dict,L32:__str__]; L36:class RuntimeLog[L39:__init__,L43:add,L48:info,L51:warning,L54:error,L57:debug]
F:L16:def __init__()->['time.strftime', 'time.time']; L23:def to_dict()->[]; L32:def __str__()->[]; L39:def __init__()->['deque']; L43:def add()->['RuntimeLogEntry', 'self._entries.append']; L48:def info()->['self.add']; L51:def warning()->['self.add']; L54:def error()->['self.add'] (+7 more)
N:-

## `runtime\seller_service.py`

I:L1:import json; L1:import time; L1:import threading; L1:import sys; L1:import os; L2:import re; L3:import uuid; L4:from concurrent.futures import ThreadPoolExecutor; L5:from pathlib import Path; L6:from typing import Optional; L6:from typing import Any; L69:import logging; L10:from dotenv import load_dotenv; L86:import threading; L1215:import time; L1215:import uuid; L1381:import re; L1381:import uuid; L1381:import time; L1593:import time
C:L73:class SellerService[L74:__init__,L89:_emit_event,L109:_match_order_to_lot,L167:load_credentials,L200:save_credentials,L212:clear_credentials]
F:L33:def _force_no_proxy()->['k.lower', 'list', 'os.environ.keys']; L41:def _safe_error()->['_re.sub', "_re.sub('\\\\s+', ' ', msg).strip", 'len', 'msg.lower']; L62:def _currency_to_symbol()->['CURRENCY_SYMBOLS.get', 'getattr', 'str']; L74:def __init__()->['_th_b169.Lock', 'threading.RLock']; L89:def _emit_event()->['bus.emit', 'event.update', 'getattr', 'print']; L109:def _match_order_to_lot()->["(l.get('title') or '').strip", 'cached_map.append', 'isinstance', 'l.get']; L167:def load_credentials()->['CREDS_FILE.exists', 'CREDS_FILE.read_text', 'CREDS_FILE.write_text', 'dict']; L200:def save_credentials()->['CREDS_FILE.write_text', '_safe_error', 'golden_key.strip', 'json.dumps'] (+180 more)
N:L3848:file_write; L4194:open; L4340:open; L4351:open; L4504:open

## `runtime\simulator.py`

I:L6:from __future__ import annotations; L8:from typing import Any; L8:from typing import Dict; L8:from typing import List; L8:from typing import Tuple
C:L11:class PluginSimulator[L16:__init__,L19:run_all]
F:L16:def __init__()->[]; L19:def run_all()->['all', 'bool', 'config.get', 'getattr']
N:-

## `runtime\snapshot_builder.py`

I:L2:from runtime.context import get_app_context; L27:from dashboard import notification_manager; L36:from dashboard import state_manager
C:L4:class SnapshotBuilder[L5:__init__,L8:build_snapshot,L76:refresh_snapshot]
F:L5:def __init__()->['get_app_context']; L8:def build_snapshot()->['all_plugins.values', 'executor._process_manager.get_all_processes', 'getattr', 'hasattr']; L76:def refresh_snapshot()->['self.build_snapshot', 'self.context.update_snapshot']
N:-

## `runtime\supplier_registry.py`

I:L1:import os; L2:import json; L3:from typing import Dict; L3:from typing import List; L3:from typing import Optional; L4:from runtime.http_client import HTTPClient
C:L6:class SupplierRegistry[L60:get_all_suppliers,L65:get_supplier,L70:get_enabled_suppliers,L75:get_api_key,L97:is_enabled,L111:get_marker]
F:L60:def get_all_suppliers()->[]; L65:def get_supplier()->['cls.SUPPLIERS.get']; L70:def get_enabled_suppliers()->['cfg.get', 'cls.SUPPLIERS.items']; L75:def get_api_key()->['cls.get_supplier', 'os.getenv', 'supplier.get']; L97:def is_enabled()->['cls.get_api_key', 'cls.get_supplier', 'supplier.get']; L111:def get_marker()->['cls.get_supplier', 'supplier.get']
N:-

## `runtime\supplier_worker.py`

I:L8:import time; L9:import queue; L10:import threading; L11:import logging; L12:from typing import Dict; L12:from typing import List; L12:from typing import Callable; L12:from typing import Optional
C:L17:class SupplierWorker[L20:__init__,L27:start,L31:stop,L35:submit,L40:active,L43:_run]; L59:class SupplierWorkerPool[L62:__init__,L65:get_worker,L72:submit,L77:stop_all,L82:active_workers]
F:L20:def __init__()->['queue.Queue', 'threading.Event', 'threading.Thread']; L27:def start()->['logger.debug', 'self._thread.start']; L31:def stop()->['self._stop.set']; L35:def submit()->['self._queue.put']; L40:def active()->[]; L43:def _run()->['callback', 'logger.error', 'self._queue.get', 'self._queue.task_done']; L62:def __init__()->[]; L65:def get_worker()->['SupplierWorker', 'self._workers[supplier].start'] (+3 more)
N:-

## `runtime\ttl_cache.py`

I:L1:import threading; L2:import time; L3:from collections import deque
C:L6:class TTLSet[L7:__init__,L13:add,L20:__contains__,L26:discard,L30:_cleanup]
F:L7:def __init__()->['deque', 'threading.Lock']; L13:def add()->['self._cleanup', 'self._queue.append', 'time.time']; L20:def __contains__()->['self._cleanup', 'time.time']; L26:def discard()->['self._data.pop']; L30:def _cleanup()->['self._data.pop', 'self._queue.popleft']
N:-

## `runtime\version.py`

I:
C:-
F:-
N:-

## `runtime\__init__.py`

I:L10:from runtime.runtime_log import RuntimeLog; L10:from runtime.runtime_log import LogLevel; L11:from runtime.runtime_controller import RuntimeController; L12:from runtime.event_types import Event; L12:from runtime.event_types import EventAction; L12:from runtime.event_types import EventResult; L12:from runtime.event_types import EventSource; L12:from runtime.event_types import EventSeverity; L13:from runtime.observability.observability_hub import ObservabilityHub; L14:from runtime.observability.event_store import EventStore; L15:from runtime.observability.metrics import MetricsCollector; L15:from runtime.observability.metrics import PluginMetrics; L16:from runtime.observability.health_engine import HealthEngineV2; L17:from runtime.websocket.websocket_hub import WebSocketHub; L18:from runtime.ai_team_orchestrator import AITeamOrchestrator; L18:from runtime.ai_team_orchestrator import LogMonitor; L18:from runtime.ai_team_orchestrator import TaskManager; L19:from runtime.ai_team.ai_team_orchestrator import AITeamOrchestrator; L20:from runtime.ai_team.model_manager import AIModelManager; L21:from runtime.ai_team.scheduled_tasks import ScheduledTasks
C:-
F:-
N:-

## `scripts\acceptance_test.py`

I:L5:from __future__ import annotations; L7:import argparse; L8:import json; L9:import os; L10:import sys; L11:import time; L12:import threading; L13:import traceback; L14:import logging; L15:import asyncio; L16:from datetime import datetime; L16:from datetime import timezone; L16:from datetime import timedelta; L17:from typing import Any; L17:from typing import Dict; L17:from typing import List; L17:from typing import Optional; L17:from typing import Tuple; L24:import sys; L25:from pathlib import Path
C:L94:class FakeSeller[L95:__init__,L102:_record,L105:has_credentials,L108:test_connection,L111:get_account_overview,L121:get_balance_full]; L467:class _FBot[L468:send_message]
F:L40:def record()->['RESULTS.append', 'print']; L45:def write_report()->['datetime.now', 'datetime.now().strftime', 'datetime.now(timezone.utc).isoformat', 'json.dump']; L69:def http()->['e.read', 'e.read().decode', 'json.dumps', 'json.dumps(json_body).encode']; L207:def _auth()->['jsonify', 'p.startswith', 'request.headers.get']; L217:def _sim()->['PluginSimulator', 'app.route', 'getattr', 'jsonify']; L224:def _health()->['app.route']; L228:def _run_server()->['app.run']; L243:def run_stage_1()->['AIAgentService', 'EmergencyManager', 'EventBus', 'OrderFlowManager'] (+35 more)
N:L59:open; L76:urllib; L78:urllib; L78:open; L418:asyncio; L421:asyncio

## `scripts\run_simulation.py`

I:L15:import os; L16:import sys; L17:import time; L18:import json; L19:import threading; L20:from pathlib import Path; L27:from dotenv import load_dotenv; L42:import funpayhub_main; L71:from runtime.database.base import init_db; L71:from runtime.database.base import get_session; L72:from runtime.database.models import Provider; L72:from runtime.database.models import Order; L72:from runtime.database.models import Transaction; L73:from runtime.database.repository import Repository; L74:from runtime.database.ledger import Ledger
C:-
F:L31:def log()->['print']; L226:def test_task()->['threading.current_thread']; L229:def callback()->['results.append']
N:L79:db; L80:db; L81:db; L82:db; L84:db; L257:open

## `scripts\sim_audit.py`

I:L13:from __future__ import annotations; L15:import os; L16:import sys; L17:import time; L18:import json; L19:import asyncio; L20:import threading; L21:import traceback; L22:from typing import Any; L22:from typing import Dict; L22:from typing import List; L22:from typing import Optional; L115:import runtime.seller_service; L120:from flask import Flask; L120:from flask import request; L120:from flask import jsonify; L121:import web.seller_api; L122:from runtime.simulator import PluginSimulator; L148:import urllib.request; L149:import urllib.error
C:L35:class FakeSeller[L37:__init__,L45:has_credentials,L46:test_connection,L48:get_my_lots,L51:get_lot_details,L57:toggle_lot_active]; L254:class _FakeBot[L255:send_message]; L413:class _Bot[L414:send_message]
F:L129:def _auth()->['jsonify', 'p.startswith', 'request.headers.get']; L138:def _sim()->['PluginSimulator', 'app.route', 'getattr', 'jsonify']; L144:def _health()->['app.route']; L152:def http()->['e.read', 'e.read().decode', 'json.dumps', 'json.dumps(json_body).encode']; L178:def _run_server()->['app.run']; L193:def record()->['RESULTS.append', 'print']; L206:def main()->['AIAgentService', 'EmergencyManager', 'EventBus', 'OrderFlowManager']; L37:def __init__()->[] (+19 more)
N:L159:urllib; L161:urllib; L161:open; L472:asyncio

## `security\secrets_manager.py`

I:L15:import json; L16:import os; L17:import re; L18:import logging; L19:from pathlib import Path; L20:from typing import Optional; L22:from cryptography.fernet import Fernet; L32:import sys
C:L140:class SecretsManager[L141:__init__,L145:encrypt_secret,L149:decrypt_secret,L153:get_encryption_key,L157:get_secret,L183:set_secret]
F:L30:def _project_root()->['Path', 'Path(__file__).resolve', 'Path(sys.executable).resolve', 'getattr']; L39:def _dotenv_path()->['_project_root']; L43:def _load_key_from_dotenv()->['_dotenv_path', 'env_file.exists', 'env_file.read_text', 'logger.warning']; L69:def _save_key_to_dotenv()->['_dotenv_path', 'env_file.exists', 'env_file.read_text', 'env_file.write_text']; L108:def _resolve_key()->['Fernet.generate_key', '_load_key_from_dotenv', '_save_key_to_dotenv', 'dotenv_key.decode']; L141:def __init__()->['Fernet', '_resolve_key']; L145:def encrypt_secret()->['secret.encode', 'self.cipher.encrypt', 'self.cipher.encrypt(secret.encode()).decode']; L149:def decrypt_secret()->['encrypted.encode', 'self.cipher.decrypt', 'self.cipher.decrypt(encrypted.encode()).decode'] (+7 more)
N:L80:db

## `security\secret_loader.py`

I:
C:-
F:-
N:-

## `tests\conftest.py`

I:L2:import os; L3:import pytest; L4:from dotenv import load_dotenv
C:-
F:-
N:-

## `tests\test_ai_team_integration.py`

I:L2:import json; L3:import pytest; L4:from unittest.mock import patch; L6:from runtime.ai_team.model_manager import AIModelManager; L7:from runtime.ai_team.scheduled_tasks import ScheduledTasks; L8:from runtime.ai_team.ai_team_orchestrator import AITeamOrchestrator
C:-
F:L12:def _mock_secrets_and_http()->['monkeypatch.setattr', 'pytest.fixture']; L32:def test_model_manager_initialization()->['AIModelManager']; L38:def test_model_manager_query_uses_primary_model()->['AIModelManager', 'manager.query']; L44:def test_scheduled_tasks_market_analysis()->['AIModelManager', 'ScheduledTasks', 'tasks.market_analysis']; L52:def test_scheduled_tasks_daily_report()->['AIModelManager', 'ScheduledTasks', 'tasks.generate_daily_report']; L60:def test_orchestrator_analyzes_errors_with_ai()->['AITeamOrchestrator', 'json.dumps', 'monkeypatch.setattr', 'orchestrator.analyze_error']; L15:def mock_get_secret()->[]; L26:def fake_post()->[] (+1 more)
N:-

## `tests\test_golden_key.py`

I:L2:import os
C:-
F:L5:def test_golden_key_exists()->['len', 'os.getenv']
N:-

## `tests\test_telegram_panel_contracts.py`

I:L2:import ast; L3:from pathlib import Path; L5:from runtime.simulator import PluginSimulator; L6:from bot.formatters import format_balance; L6:from bot.formatters import format_market_status
C:L86:class Plugin[]; L89:class Manager[]
F:L12:def _callback_values()->['ast.walk', 'getattr', 'isinstance', 'set']; L22:def _handled_callbacks()->['ast.walk', 'getattr', 'isinstance', 'set']; L56:def test_each_main_menu_callback_has_a_handler()->['_handled_callbacks', 'ast.parse', 'path.exists', 'path.read_text']; L73:def test_formatters_do_not_return_raw_json_or_unescaped_html()->['format_balance', 'format_market_status']; L85:def test_simulation_is_diagnostic_and_does_not_require_network()->['Manager', 'Plugin', 'PluginSimulator', 'PluginSimulator(Manager()).run_all']
N:-

## `web\alerts_api.py`

I:L1:from flask import Blueprint; L1:from flask import jsonify; L1:from flask import request; L1:from flask import current_app; L2:import sys; L2:import os; L4:from runtime.notifications.notification_manager import NotificationManager; L5:from runtime.notifications.notification_types import Notification; L5:from runtime.notifications.notification_types import NotificationType
C:-
F:L11:def _get_manager()->['getattr']; L19:def list_alerts()->['_get_manager', 'alerts_bp.route', 'int', 'isinstance']; L35:def alerts_stats()->['_get_manager', 'alerts_bp.route', 'jsonify']; L41:def ack_alert()->['_get_manager', 'alerts_bp.route', 'jsonify', 'nm.acknowledge']; L50:def dismiss_alert()->['_get_manager', 'alerts_bp.route', 'jsonify', 'nm.dismiss']; L59:def clear_alerts()->['_get_manager', 'alerts_bp.route', 'jsonify', 'nm.clear_history']; L66:def create_test_alert()->['Notification', 'NotificationType', '_get_manager', 'alerts_bp.route']
N:-

## `web\assistant_api.py`

I:L8:from flask import Blueprint; L8:from flask import jsonify; L8:from flask import request; L9:import json; L9:import time; L10:from pathlib import Path; L11:from security.secrets_manager import SecretsManager; L13:from runtime.http_client import HTTPClient; L13:from runtime.http_client import HTTPClientError; L24:import sys; L98:from bot.config import get_hub_url; L412:import uuid
C:-
F:L23:def _base_dir()->["(parent / 'funpayhub_main.py').exists", 'Path', 'Path(__file__).resolve', 'Path(sys.executable).resolve']; L45:def _load_keys()->['KEYS_FILE.exists', 'KEYS_FILE.read_text', 'SECRETS.get_secret', 'isinstance']; L61:def _save_keys()->['KEYS_FILE.write_text', 'data.get', 'json.dumps']; L76:def _load_history()->['HISTORY_FILE.exists', 'HISTORY_FILE.read_text', 'json.loads']; L84:def _save_history()->['HISTORY_FILE.write_text', 'json.dumps']; L95:def _gather_context()->['_fetch', '_http_client.get', 'a.get', 'alerts.get']; L213:def _kb_lookup()->['KB_FAQ.items', 'question.lower']; L226:def _call_openai()->['_http_client.post', 'str'] (+10 more)
N:-

## `web\funpay_proxy.py`

I:L5:from flask import Blueprint; L5:from flask import jsonify; L5:from flask import request; L5:from flask import current_app; L6:import re; L7:import time; L9:from runtime.http_client import HTTPClient; L9:from runtime.http_client import HTTPClientError; L23:from runtime.seller_service import seller_service_singleton; L43:from bot.config import get_hub_url
C:-
F:L19:def _get_user_id_from_seller_service()->['_http_client.get', 'get_hub_url', 'getattr', 'hasattr']; L53:def _scrape_profile()->['_http_client.get', 'avatar.startswith', 'float', 'int']; L147:def get_profile()->['_cache.get', '_scrape_profile', 'data.get', 'funpay_proxy_bp.route']; L160:def get_me()->['_get_user_id_from_seller_service', 'funpay_proxy_bp.route', 'get_profile', 'jsonify']; L173:def debug()->['_get_user_id_from_seller_service', 'funpay_proxy_bp.route', 'jsonify', 'len']
N:-

## `web\health.py`

I:
C:-
F:-
N:-

## `web\logs_api.py`

I:L1:from flask import Blueprint; L1:from flask import jsonify; L1:from flask import request; L1:from flask import current_app; L1:from flask import Response; L2:import sys; L2:import os; L2:import json; L2:import time; L4:from runtime.runtime_log import RuntimeLog; L4:from runtime.runtime_log import LogLevel
C:-
F:L10:def _get_runtime_log()->['getattr']; L17:def _get_observability()->['getattr']; L21:def _seed_demo_logs()->['rl.count', 'rl.debug', 'rl.error', 'rl.info']; L33:def list_logs()->['LogLevel', '_get_runtime_log', '_seed_demo_logs', "e['message'].lower"]; L56:def logs_stats()->['_get_runtime_log', '_seed_demo_logs', 'by_level.get', 'e.get']; L70:def clear_logs()->['_get_runtime_log', 'jsonify', 'logs_bp.route', 'rl.clear']; L77:def export_logs()->["'\\n'.join", 'Response', '_get_runtime_log', 'e.get']; L92:def add_test_log()->['LogLevel', '_get_runtime_log', 'body.get', "body.get('level', 'INFO').upper"] (+1 more)
N:-

## `web\plugin_management_api.py`

I:L1:from flask import Blueprint; L1:from flask import jsonify; L1:from flask import request; L2:import sys; L2:import os; L2:import json; L3:from pathlib import Path; L4:from datetime import datetime; L8:from runtime.plugin_config_manager import PluginConfigManager; L9:from runtime.dependency_resolver import DependencyResolver; L20:from flask import current_app; L213:from flask import current_app; L244:from flask import current_app; L274:from flask import current_app; L307:from flask import current_app; L266:import traceback
C:-
F:L19:def _runtime_controller()->['getattr']; L24:def _load_history()->['HISTORY_FILE.exists', 'HISTORY_FILE.read_text', 'json.loads']; L33:def _save_history()->['HISTORY_FILE.write_text', 'json.dumps']; L37:def _record_history()->['_load_history', '_save_history', 'datetime.now', 'datetime.now().strftime']; L51:def _get_plugins_data()->['_runtime_controller', 'rc.list_plugins', 'result.get', "result.get('data', {}).get"]; L67:def get_all_plugins()->['_get_plugins_data', 'config.get', 'config_manager.create_default_config', 'config_manager.get_config']; L93:def get_plugin_details()->['_load_history', '_load_history().get', '_runtime_controller', 'config_manager.create_default_config']; L118:def enable_plugin()->['_record_history', '_runtime_controller', 'config_manager.create_default_config', 'config_manager.get_config'] (+11 more)
N:-

## `web\seller_api.py`

I:L1:from flask import Blueprint; L1:from flask import jsonify; L1:from flask import request; L2:import sys; L2:import os; L4:from runtime.seller_service import seller_service_singleton; L930:import threading; L6:from runtime.lot_generator import LotGenerator; L219:from flask import request; L655:from flask import send_file; L980:import time; L1010:import time; L1028:import time; L1028:import uuid; L1068:import time; L1100:import os; L1100:import json; L1100:import sys; L1119:import re; L1285:import random
C:-
F:L14:def version()->['jsonify', 'seller_bp.route']; L19:def status()->['jsonify', 'seller_bp.route', 'svc.has_credentials']; L24:def set_credentials()->['body.get', "body.get('golden_key', '').strip", "body.get('user_agent', '').strip", 'jsonify']; L38:def delete_credentials()->['jsonify', 'seller_bp.route', 'svc.clear_credentials']; L43:def overview()->['jsonify', 'request.args.get', "request.args.get('force', 'false').lower", 'seller_bp.route']; L49:def balance()->['int', 'jsonify', 'request.args.get', 'seller_bp.route']; L55:def balance_full()->['jsonify', 'request.args.get', "request.args.get('force', 'false').lower", 'seller_bp.route']; L61:def balance_history()->['int', 'jsonify', 'request.args.get', 'seller_bp.route'] (+138 more)
N:L941:open; L949:open; L1108:open

## `web\userdata_api.py`

I:L6:from flask import Blueprint; L6:from flask import request; L6:from flask import jsonify; L6:from flask import send_from_directory; L6:from flask import abort; L7:import sys; L7:import os; L7:import uuid; L7:import hashlib; L8:from pathlib import Path
C:-
F:L18:def _userdata_root()->["(parent / 'funpayhub_main.py').exists", 'Path', 'Path(__file__).resolve', 'Path(sys.executable).resolve']; L48:def _safe_filename()->['Path', 'Path(original).suffix.lower', 'hashlib.sha1', 'hashlib.sha1(content).hexdigest']; L56:def upload()->["(request.form.get('type') or '').strip", "(request.form.get('type') or '').strip().lower", 'Path', "Path(f.filename or '').suffix.lower"]; L103:def list_files()->["(request.args.get('type') or '').strip", "(request.args.get('type') or '').strip().lower", 'files.append', 'folder.exists']; L123:def delete()->["(body.get('name') or '').strip", "(body.get('type') or '').strip", "(body.get('type') or '').strip().lower", 'body.get']; L144:def serve_userdata()->['abort', 'send_from_directory', 'str', 'userdata_bp.route']
N:-

## `runtime\ai_team\ai_team_orchestrator.py`

I:L1:import json; L2:import logging; L3:import re; L4:import threading; L5:import time; L6:from typing import Any; L6:from typing import Dict; L6:from typing import Optional; L8:from runtime.ai_team.model_manager import AIModelManager
C:L13:class AITeamOrchestrator[L14:__init__,L21:_load_config,L30:analyze_error,L59:run_24_7]
F:L14:def __init__()->['AIModelManager', 'self._load_config']; L21:def _load_config()->['isinstance', 'json.load', 'logger.warning', 'open']; L30:def analyze_error()->['isinstance', 'json.loads', 'json_match.group', 'logger.warning']; L59:def run_24_7()->['self.config.get', "self.config.get('schedule', {}).get", 'time.sleep']
N:L23:open

## `runtime\ai_team\model_manager.py`

I:L8:import json; L9:import logging; L10:from pathlib import Path; L11:from typing import Any; L11:from typing import Dict; L11:from typing import Optional; L13:from runtime.http_client import HTTPClient; L13:from runtime.http_client import HTTPClientError; L14:from security.secrets_manager import SecretsManager; L75:import time
C:L26:class AIModelManager[L27:__init__,L33:_load_config,L42:_resolve_api_key,L58:query,L97:_query_groq,L126:_query_google]
F:L27:def __init__()->['HTTPClient', 'SecretsManager', 'self._load_config', 'self.config.get']; L33:def _load_config()->['json.load', 'logger.error', 'open']; L42:def _resolve_api_key()->['_ENV_KEYS.get', 'model_cfg.get', 'self.models.get', 'self.secrets.get_secret']; L58:def query()->['logger.error', 'logger.warning', 'range', 'self._query_google']; L97:def _query_groq()->['logger.warning', 'messages.append', 'model_config.get', 'self._resolve_api_key']; L126:def _query_google()->['logger.warning', 'model_config.get', 'self._resolve_api_key', 'self.http_client.post']; L149:def _query_openrouter()->['logger.warning', 'messages.append', 'model_config.get', 'self._resolve_api_key']
N:L36:open

## `runtime\ai_team\scheduled_tasks.py`

I:L4:import logging; L5:from datetime import datetime; L6:from typing import Any; L6:from typing import Dict
C:L11:class ScheduledTasks[L12:__init__,L16:market_analysis,L34:code_review,L55:generate_daily_report]
F:L12:def __init__()->['model_manager.config.get']; L16:def market_analysis()->['datetime.now', 'datetime.now().isoformat', 'self.model_manager.query']; L34:def code_review()->['datetime.now', 'datetime.now().isoformat', 'self.model_manager.query']; L55:def generate_daily_report()->['datetime.now', 'datetime.now().isoformat', 'datetime.now().strftime', 'self.model_manager.query']
N:-

## `runtime\ai_team\__init__.py`

I:L1:from runtime.ai_team.ai_team_orchestrator import AITeamOrchestrator; L2:from runtime.ai_team.model_manager import AIModelManager; L3:from runtime.ai_team.scheduled_tasks import ScheduledTasks
C:-
F:-
N:-

## `runtime\automation\approval_manager.py`

I:L1:import json; L2:from pathlib import Path; L3:from datetime import datetime
C:L5:class ApprovalManager[L6:__init__,L10:request_approval,L21:approve,L31:is_approved]
F:L6:def __init__()->['self.approval_dir.mkdir']; L10:def request_approval()->['approval_file.write_text', 'datetime.utcnow', 'datetime.utcnow().isoformat', 'json.dumps']; L21:def approve()->['approval_file.exists', 'approval_file.read_text', 'approval_file.write_text', 'datetime.utcnow']; L31:def is_approved()->['approval_file.exists', 'approval_file.read_text', 'data.get', 'json.loads']
N:-

## `runtime\automation\execution_history.py`

I:L1:import json; L2:from pathlib import Path; L3:from datetime import datetime; L4:from typing import List; L4:from typing import Dict
C:L6:class ExecutionHistory[L7:__init__,L11:log,L26:get_last]
F:L7:def __init__()->['self.history_file.parent.mkdir']; L11:def log()->['datetime.utcnow', 'datetime.utcnow().isoformat', 'history.append', 'json.dumps']; L26:def get_last()->['json.loads', 'self.history_file.exists', 'self.history_file.read_text']
N:-

## `runtime\automation\patch_executor.py`

I:L1:import shutil; L2:import tempfile; L3:from pathlib import Path; L4:from datetime import datetime; L5:from typing import List; L5:from typing import Tuple; L6:from task_package import TaskPackage; L7:from patch_validator import PatchValidator
C:L9:class PatchExecutor[L10:__init__,L15:apply]
F:L10:def __init__()->['PatchValidator']; L15:def apply()->['Path', 'datetime.now', 'datetime.now().strftime', 'dest.parent.mkdir']
N:-

## `runtime\automation\patch_validator.py`

I:L1:import subprocess; L2:import sys; L3:import tempfile; L4:from pathlib import Path; L5:from typing import List; L5:from typing import Tuple; L6:from task_package import TaskPackage
C:L8:class PatchValidator[L9:__init__,L12:validate_files,L24:syntax_check]
F:L9:def __init__()->[]; L12:def validate_files()->['any', 'errors.append', 'full_path.resolve', 'full_path.resolve().relative_to']; L24:def syntax_check()->['Path', 'dest.parent.mkdir', 'dest.write_text', 'fc.path.endswith']
N:L33:subprocess

## `runtime\automation\rollback_manager.py`

I:L1:import shutil; L2:from pathlib import Path; L3:from typing import List
C:L5:class RollbackManager[L6:__init__,L9:rollback]
F:L6:def __init__()->[]; L9:def rollback()->['Path', 'path.replace', 'print', 'self.backups_dir.glob']
N:L9:db

## `runtime\automation\task_package.py`

I:L1:import json; L2:from dataclasses import dataclass; L2:from dataclasses import field; L3:from typing import List; L3:from typing import Dict; L3:from typing import Optional; L4:from datetime import datetime
C:L7:class FileChange[]; L13:class TaskPackage[L24:to_dict,L38:from_dict,L52:save,L57:load]
F:L24:def to_dict()->[]; L38:def from_dict()->['FileChange', 'cls', 'data.get']; L52:def save()->['json.dump', 'open', 'self.to_dict']; L57:def load()->['cls.from_dict', 'json.load', 'open']
N:L21:db; L33:db; L48:db; L53:open; L58:open

## `runtime\automation\__init__.py`

I:L1:from task_package import TaskPackage; L1:from task_package import FileChange; L2:from patch_validator import PatchValidator; L3:from patch_executor import PatchExecutor; L4:from rollback_manager import RollbackManager; L5:from approval_manager import ApprovalManager; L6:from execution_history import ExecutionHistory
C:-
F:-
N:L4:db

## `runtime\backup\backup_manager.py`

I:L2:import os; L3:import json; L4:import zipfile; L5:import hashlib; L6:import shutil; L7:from datetime import datetime; L8:from typing import Dict; L8:from typing import Any; L8:from typing import Optional; L9:from runtime.backup.models import BackupMetadata; L9:from runtime.backup.models import BackupInfo
C:L12:class BackupManager[L13:__init__,L18:_get_state_manager,L27:_get_plugin_manager,L30:_get_observability_hub,L35:_get_recovery_manager,L40:_get_boot_journal]
F:L13:def __init__()->['os.makedirs']; L18:def _get_state_manager()->['hasattr']; L27:def _get_plugin_manager()->[]; L30:def _get_observability_hub()->['hasattr']; L35:def _get_recovery_manager()->['hasattr']; L40:def _get_boot_journal()->['getattr', 'hasattr']; L45:def create_backup()->['BackupInfo', 'BackupMetadata', 'boot_journal.load', 'datetime.utcnow']; L120:def _create_snapshot()->['datetime.utcnow', 'datetime.utcnow().timestamp', 'obs.get_detailed_health', 'obs.get_plugin_metrics'] (+5 more)
N:L60:open; L66:open; L71:open; L79:open; L85:open; L92:open

## `runtime\backup\models.py`

I:L2:from dataclasses import dataclass; L2:from dataclasses import field; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Optional; L3:from typing import List; L4:from datetime import datetime
C:L8:class BackupMetadata[]; L18:class BackupInfo[]
F:-
N:-

## `runtime\backup\restore_manager.py`

I:L2:import os; L3:import json; L4:import zipfile; L5:import shutil; L6:import tempfile; L7:from typing import Dict; L7:from typing import Any; L8:from runtime.backup.models import BackupInfo
C:L11:class RestoreManager[L12:__init__,L25:restore_from_backup]
F:L12:def __init__()->['getattr', 'hasattr']; L25:def restore_from_backup()->['json.load', 'open', 'os.path.exists', 'os.path.join']
N:L39:open; L53:open; L60:open; L69:open

## `runtime\backup\scheduler.py`

I:L2:import threading; L3:import time; L4:from typing import Optional; L5:from runtime.backup.backup_manager import BackupManager
C:L8:class BackupScheduler[L9:__init__,L17:start,L26:stop,L33:_loop,L39:_create_backup_and_rotate,L48:_rotate_backups]
F:L9:def __init__()->['threading.Event']; L17:def start()->['print', 'self._stop_event.clear', 'self._thread.start', 'threading.Thread']; L26:def stop()->['print', 'self._stop_event.set', 'self._thread.join']; L33:def _loop()->['self._create_backup_and_rotate', 'self._stop_event.wait']; L39:def _create_backup_and_rotate()->['print', 'self._rotate_backups', 'self.backup_manager.create_backup']; L48:def _rotate_backups()->['len', 'print', 'self.backup_manager.delete_backup', 'self.backup_manager.list_backups']
N:-

## `runtime\backup\__init__.py`

I:L2:from runtime.backup.models import BackupMetadata; L2:from runtime.backup.models import BackupInfo; L3:from runtime.backup.backup_manager import BackupManager; L4:from runtime.backup.restore_manager import RestoreManager; L5:from runtime.backup.scheduler import BackupScheduler
C:-
F:-
N:-

## `runtime\cache\cache_manager.py`

I:L8:from __future__ import annotations; L10:import time; L11:from threading import RLock
C:L14:class CacheManager[L17:__init__,L22:get,L33:set,L38:invalidate,L42:clear,L46:snapshot]
F:L17:def __init__()->['RLock']; L22:def get()->['self._store.get', 'self._store.pop', 'time.time']; L33:def set()->['time.time']; L38:def invalidate()->['self._store.pop']; L42:def clear()->['self._store.clear']; L46:def snapshot()->['dict']
N:-

## `runtime\cache\__init__.py`

I:
C:-
F:-
N:-

## `runtime\database\base.py`

I:L6:import os; L7:import threading; L8:from pathlib import Path; L9:from sqlalchemy import create_engine; L9:from sqlalchemy import event; L10:from sqlalchemy.orm import sessionmaker; L10:from sqlalchemy.orm import scoped_session; L10:from sqlalchemy.orm import declarative_base; L78:from runtime.database.models import User; L78:from runtime.database.models import Order; L78:from runtime.database.models import Product; L78:from runtime.database.models import Lot; L78:from runtime.database.models import Provider; L78:from runtime.database.models import Transaction; L78:from runtime.database.models import Review; L78:from runtime.database.models import Log; L78:from runtime.database.models import ProviderBalance
C:-
F:L19:def _resolve_db_path()->['Path', 'Path(__file__).resolve', 'abs_path.as_posix', 'abs_path.parent.mkdir']; L31:def get_engine()->['_resolve_db_path', 'create_engine', 'cursor.close', 'cursor.execute']; L62:def get_session()->['_session_factory', 'get_engine', 'scoped_session', 'sessionmaker']; L75:def init_db()->['Base.metadata.create_all', 'get_engine']; L86:def shutdown_db()->['_engine.dispose', '_session_factory.remove']; L53:def _set_sqlite_pragma()->['cursor.close', 'cursor.execute', 'db_url.startswith', 'dbapi_connection.cursor']
N:L56:db; L57:db; L70:db

## `runtime\database\ledger.py`

I:L20:import time; L21:from decimal import Decimal; L22:from typing import Optional; L22:from typing import List; L22:from typing import Dict; L22:from typing import Any; L23:from sqlalchemy import func; L25:from runtime.database.base import get_session; L26:from runtime.database.models import Transaction; L26:from runtime.database.models import Order; L26:from runtime.database.models import Provider
C:L29:class Ledger[L35:record,L88:record_order_income,L102:record_provider_payment,L118:record_commission,L132:record_refund,L146:record_profit]
F:L35:def record()->['Transaction', 'get_session', 'session.add', 'session.close']; L88:def record_order_income()->['Ledger.record', 'abs']; L102:def record_provider_payment()->['Ledger.record', 'abs']; L118:def record_commission()->['Ledger.record', 'abs']; L132:def record_refund()->['Ledger.record', 'abs']; L146:def record_profit()->['Ledger.record']; L160:def record_deposit()->['Ledger.record', 'abs']; L174:def get_order_transactions()->['get_session', 'session.close', 'session.query', 'session.query(Transaction).filter'] (+4 more)
N:L54:db; L63:db; L78:db; L79:db; L82:db; L179:db

## `runtime\database\models.py`

I:L16:import time; L17:from sqlalchemy import Column; L17:from sqlalchemy import Integer; L17:from sqlalchemy import String; L17:from sqlalchemy import Float; L17:from sqlalchemy import BigInteger; L17:from sqlalchemy import Text; L17:from sqlalchemy import DateTime; L17:from sqlalchemy import ForeignKey; L17:from sqlalchemy import Enum; L17:from sqlalchemy import JSON; L17:from sqlalchemy import Boolean; L17:from sqlalchemy import Index; L22:from sqlalchemy.orm import relationship; L23:from runtime.database.base import Base; L25:import enum
C:L30:class OrderStatus(str,enum.Enum)[]; L39:class TransactionType(str,enum.Enum)[]; L49:class ProviderStatus(str,enum.Enum)[]; L56:class LotStatus(str,enum.Enum)[]; L65:class User(Base)[L77:__repr__]; L81:class Product(Base)[L98:__repr__]; L102:class Lot(Base)[L119:__repr__]; L123:class Provider(Base)[L139:__repr__]; L143:class Order(Base)[L174:__repr__]; L182:class Transaction(Base)[L200:__repr__]; L208:class Review(Base)[L224:__repr__]; L228:class Log(Base)[]; L245:class ProviderBalance(Base)[]
F:L77:def __repr__()->[]; L98:def __repr__()->[]; L119:def __repr__()->[]; L139:def __repr__()->[]; L174:def __repr__()->[]; L200:def __repr__()->[]; L224:def __repr__()->[]
N:-

## `runtime\database\repository.py`

I:L7:import time; L8:from typing import Optional; L8:from typing import List; L8:from typing import Dict; L8:from typing import Any; L9:from sqlalchemy import func; L11:from runtime.database.base import get_session; L12:from runtime.database.models import User; L12:from runtime.database.models import Order; L12:from runtime.database.models import Product; L12:from runtime.database.models import Lot; L12:from runtime.database.models import Provider; L12:from runtime.database.models import Transaction; L12:from runtime.database.models import Review; L12:from runtime.database.models import Log; L12:from runtime.database.models import ProviderBalance; L12:from runtime.database.models import OrderStatus
C:L19:class Repository[L25:get_or_create_user,L67:create_order,L99:get_order,L109:get_order_by_id,L117:update_order_status,L143:get_active_orders]
F:L25:def get_or_create_user()->['User', 'get_session', 'session.add', 'session.close']; L67:def create_order()->['Order', 'get_session', 'session.add', 'session.close']; L99:def get_order()->['get_session', 'session.close', 'session.query', 'session.query(Order).filter']; L109:def get_order_by_id()->['get_session', 'session.close', 'session.query', 'session.query(Order).get']; L117:def update_order_status()->['extra.items', 'get_session', 'hasattr', 'session.close']; L143:def get_active_orders()->['Order.status.in_', 'get_session', 'session.close', 'session.query']; L157:def get_orders_by_status()->['Order.started_at.desc', 'get_session', 'session.close', 'session.query']; L171:def count_orders()->['func.count', 'get_session', 'session.close', 'session.query'] (+8 more)
N:L34:db; L38:db; L47:db; L48:db; L56:db; L59:db

## `runtime\database\__init__.py`

I:L11:from runtime.database.base import get_engine; L11:from runtime.database.base import get_session; L11:from runtime.database.base import init_db; L11:from runtime.database.base import shutdown_db; L11:from runtime.database.base import Base; L18:from runtime.database.models import User; L18:from runtime.database.models import Order; L18:from runtime.database.models import Product; L18:from runtime.database.models import Lot; L18:from runtime.database.models import Provider; L18:from runtime.database.models import Transaction; L18:from runtime.database.models import Review; L18:from runtime.database.models import Log; L18:from runtime.database.models import ProviderBalance; L29:from runtime.database.ledger import Ledger; L30:from runtime.database.repository import Repository
C:-
F:-
N:-

## `runtime\export\export_manager.py`

I:L2:import json; L3:from typing import Dict; L3:from typing import Any; L4:from runtime.export.models import ExportData; L4:from runtime.export.models import PluginExport; L5:from runtime.export.schema import get_schema; L36:from runtime.export.models import RuntimeSettingsExport; L50:from runtime.export.models import ObservabilityExport; L58:from runtime.export.models import NotificationsExport
C:L8:class ExportManager[L9:__init__,L14:create_export,L35:_get_runtime_settings,L49:_get_observability_settings,L57:_get_notifications_settings,L67:export_to_json]
F:L9:def __init__()->[]; L14:def create_export()->['ExportData', 'PluginExport', 'export.plugins.append', 'plugin.PLUGIN_INFO.get']; L35:def _get_runtime_settings()->['RuntimeSettingsExport', 'getattr']; L49:def _get_observability_settings()->['ObservabilityExport']; L57:def _get_notifications_settings()->['NotificationsExport', 'self.config.get']; L67:def export_to_json()->['json.dumps', 'self.create_export']
N:-

## `runtime\export\import_manager.py`

I:L2:import json; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Tuple; L3:from typing import List; L4:from runtime.export.schema import validate_export; L5:from runtime.export.validators import validate_plugins; L5:from runtime.export.validators import validate_runtime_settings; L5:from runtime.export.validators import validate_observability; L5:from runtime.export.validators import validate_notifications
C:L8:class ImportManager[L9:__init__,L13:import_from_json,L51:_calculate_changes,L57:_merge_plugins,L93:_merge_runtime_settings,L112:_merge_observability]
F:L9:def __init__()->[]; L13:def import_from_json()->['changes.extend', 'json.loads', 'len', 'self._calculate_changes']; L51:def _calculate_changes()->[]; L57:def _merge_plugins()->['changes.append', 'plugin.get_config', 'plugin.is_enabled', 'plugin.save_config']; L93:def _merge_runtime_settings()->['changes.append', 'new_thresholds.get']; L112:def _merge_observability()->[]; L116:def _merge_notifications()->['changes.append', 'self.runtime_controller.config.get']; L125:def _report()->[]
N:-

## `runtime\export\models.py`

I:L2:from dataclasses import dataclass; L2:from dataclasses import field; L3:from typing import List; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Optional; L4:from datetime import datetime
C:L8:class PluginExport[]; L19:class RuntimeSettingsExport[]; L33:class ObservabilityExport[]; L40:class NotificationsExport[]; L49:class ExportData[]
F:-
N:-

## `runtime\export\schema.py`

I:L2:import json; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Tuple; L3:from typing import Optional; L4:from datetime import datetime; L5:from runtime.export.models import ExportData; L52:from runtime.export.models import PluginExport
C:-
F:L8:def get_schema()->[]; L22:def validate_export()->['ExportData', 'PluginExport', 'data.get', "data['data'].get"]
N:-

## `runtime\export\validators.py`

I:L2:from typing import List; L2:from typing import Tuple; L3:from runtime.export.models import ExportData
C:-
F:L6:def validate_plugins()->['warnings.append']; L14:def validate_runtime_settings()->['export_data.runtime_settings.health_thresholds.get', 'warnings.append']; L23:def validate_observability()->['warnings.append']; L30:def validate_notifications()->['export_data.notifications.discord_webhook.startswith', 'warnings.append']
N:-

## `runtime\export\__init__.py`

I:L2:from runtime.export.models import ExportData; L2:from runtime.export.models import PluginExport; L2:from runtime.export.models import RuntimeSettingsExport; L2:from runtime.export.models import ObservabilityExport; L2:from runtime.export.models import NotificationsExport; L3:from runtime.export.export_manager import ExportManager; L4:from runtime.export.import_manager import ImportManager; L5:from runtime.export.schema import validate_export; L5:from runtime.export.schema import get_schema; L6:from runtime.export.validators import validate_plugins; L6:from runtime.export.validators import validate_runtime_settings; L6:from runtime.export.validators import validate_observability; L6:from runtime.export.validators import validate_notifications
C:-
F:-
N:-

## `runtime\migrations\backup_migrations.py`

I:
C:-
F:-
N:-

## `runtime\migrations\base.py`

I:L2:from abc import ABC; L2:from abc import abstractmethod; L3:from typing import Any; L3:from typing import Dict
C:L5:class BaseMigration(ABC)[L8:from_version,L13:to_version,L17:apply]
F:L8:def from_version()->[]; L13:def to_version()->[]; L17:def apply()->[]
N:-

## `runtime\migrations\export_migrations.py`

I:L2:from typing import Any; L2:from typing import Dict; L3:from runtime.migrations.migration_base import BaseMigration; L4:from runtime.migrations.migration_registry import get_registry
C:-
F:-
N:-

## `runtime\migrations\migration_base.py`

I:L2:from abc import ABC; L2:from abc import abstractmethod; L3:from typing import Any; L3:from typing import Dict
C:L6:class BaseMigration(ABC)[L8:apply,L13:from_version,L18:to_version]
F:L8:def apply()->[]; L13:def from_version()->[]; L18:def to_version()->[]
N:-

## `runtime\migrations\migration_manager.py`

I:L2:from typing import Any; L2:from typing import Dict; L2:from typing import List; L2:from typing import Tuple; L3:from runtime.migrations.migration_registry import get_registry
C:L6:class MigrationPathNotFoundError(Exception)[]; L10:class MigrationManager[L11:__init__,L17:_migrate_chain,L41:migrate_export,L51:migrate_snapshot,L59:migrate_backup,L67:get_current_versions]
F:L11:def __init__()->['get_registry']; L17:def _migrate_chain()->['MigrationPathNotFoundError', 'get_migration_func', 'migration.apply', 'steps.append']; L41:def migrate_export()->['data.get', 'self._migrate_chain']; L51:def migrate_snapshot()->['data.get', 'self._migrate_chain']; L59:def migrate_backup()->['data.get', 'self._migrate_chain']; L67:def get_current_versions()->[]
N:-

## `runtime\migrations\migration_registry.py`

I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Optional; L3:from runtime.migrations.migration_base import BaseMigration
C:L6:class MigrationRegistry[L7:__init__,L12:register_export,L15:register_snapshot,L18:register_backup,L21:get_export_migration,L24:get_snapshot_migration]
F:L42:def get_registry()->[]; L7:def __init__()->[]; L12:def register_export()->[]; L15:def register_snapshot()->[]; L18:def register_backup()->[]; L21:def get_export_migration()->['self._export_migrations.get']; L24:def get_snapshot_migration()->['self._snapshot_migrations.get']; L27:def get_backup_migration()->['self._backup_migrations.get'] (+3 more)
N:-

## `runtime\migrations\registry.py`

I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Optional; L3:from runtime.migrations.base import BaseMigration
C:L5:class MigrationRegistry[L6:__init__,L11:register_export,L14:register_snapshot,L17:register_backup,L20:get_export_migration,L23:get_snapshot_migration]
F:L40:def get_registry()->[]; L6:def __init__()->[]; L11:def register_export()->[]; L14:def register_snapshot()->[]; L17:def register_backup()->[]; L20:def get_export_migration()->['self._export_migrations.get']; L23:def get_snapshot_migration()->['self._snapshot_migrations.get']; L26:def get_backup_migration()->['self._backup_migrations.get'] (+3 more)
N:-

## `runtime\migrations\snapshot_migrations.py`

I:
C:-
F:-
N:-

## `runtime\migrations\__init__.py`

I:L2:from runtime.migrations.migration_manager import MigrationManager; L3:from runtime.migrations.migration_registry import MigrationRegistry; L4:from runtime.migrations.migration_base import BaseMigration
C:-
F:-
N:-

## `runtime\notifications\notification_manager.py`

I:L2:from runtime.notifications.notification_types import Notification; L3:from runtime.notifications.notification_queue import NotificationQueue; L4:from runtime.notifications.rate_limiter import RateLimiter; L5:from runtime.notifications.notification_rules import NotificationRules
C:L7:class NotificationManager[L8:__init__,L14:register_channel,L17:subscribe_to_event_bus,L22:_on_event,L28:_on_health_update,L33:send]
F:L8:def __init__()->['NotificationQueue', 'NotificationRules', 'RateLimiter']; L14:def register_channel()->['self._channels.append']; L17:def subscribe_to_event_bus()->['event_bus.subscribe']; L22:def _on_event()->['event.to_dict', 'hasattr', 'self._rules.evaluate_event', 'self.send']; L28:def _on_health_update()->['data.get', 'self._rules.evaluate_health', 'self.send']; L33:def send()->['channel.send', 'notification.to_dict', 'print', 'self._queue.add']; L45:def get_history()->['self._queue.get_last']; L48:def clear_history()->['self._queue.clear']
N:-

## `runtime\notifications\notification_queue.py`

I:L2:from collections import deque; L3:import threading; L4:from typing import List
C:L6:class NotificationQueue[L7:__init__,L11:add,L15:get_all,L19:get_last,L23:clear,L27:count]
F:L7:def __init__()->['deque', 'threading.Lock']; L11:def add()->['self._queue.append']; L15:def get_all()->['list']; L19:def get_last()->['list']; L23:def clear()->['self._queue.clear']; L27:def count()->['len']
N:-

## `runtime\notifications\notification_rules.py`

I:L2:from runtime.notifications.notification_types import Notification; L2:from runtime.notifications.notification_types import NotificationType; L3:import time
C:L5:class NotificationRules[L6:__init__,L10:evaluate_event,L51:evaluate_health]
F:L6:def __init__()->[]; L10:def evaluate_event()->['Notification', 'event_dict.get', 'len', 'notifications.append']; L51:def evaluate_health()->['Notification', 'notifications.append']
N:-

## `runtime\notifications\notification_types.py`

I:L2:from enum import Enum; L3:from dataclasses import dataclass; L3:from dataclasses import field; L4:import time; L5:import uuid
C:L7:class NotificationType(Enum)[]; L15:class Notification[L24:to_dict]
F:L24:def to_dict()->[]
N:-

## `runtime\notifications\rate_limiter.py`

I:L2:import time; L3:from collections import defaultdict; L4:from typing import Dict; L4:from typing import List
C:L6:class RateLimiter[L7:__init__,L11:allow]
F:L7:def __init__()->['defaultdict']; L11:def allow()->['len', 'self._records[key].append', 'time.time']
N:-

## `runtime\notifications\__init__.py`

I:L2:from runtime.notifications.notification_manager import NotificationManager; L3:from runtime.notifications.notification_types import Notification; L3:from runtime.notifications.notification_types import NotificationType; L4:from runtime.notifications.channels.log_channel import LogChannel; L5:from runtime.notifications.channels.dashboard_channel import DashboardChannel; L6:from runtime.notifications.channels.discord_channel import DiscordChannel
C:-
F:-
N:-

## `runtime\observability\event_store.py`

I:L2:from collections import deque; L3:from typing import List; L3:from typing import Optional; L4:from runtime.event_types import Event; L4:from runtime.event_types import EventSeverity
C:L7:class EventStore[L8:__init__,L11:add,L14:get_all,L17:get_by_correlation,L20:get_by_plugin,L23:get_by_severity]
F:L8:def __init__()->['deque']; L11:def add()->['self._events.append']; L14:def get_all()->['list']; L17:def get_by_correlation()->[]; L20:def get_by_plugin()->[]; L23:def get_by_severity()->[]; L26:def get_errors()->['self.get_by_severity']; L29:def clear()->['self._events.clear'] (+2 more)
N:-

## `runtime\observability\health_engine.py`

I:L2:from runtime.observability.metrics import MetricsCollector; L3:from runtime.observability.event_store import EventStore
C:L6:class HealthEngineV2[L7:__init__,L11:calculate_score,L25:get_status,L37:get_detailed_health]
F:L7:def __init__()->[]; L11:def calculate_score()->['int', 'm.get', 'max', 'min']; L25:def get_status()->['self.calculate_score']; L37:def get_detailed_health()->['self._event_store.get_stats', 'self._metrics.get_summary', 'self.calculate_score', 'self.get_status']
N:-

## `runtime\observability\metrics.py`

I:L2:import time; L3:from collections import defaultdict; L4:from typing import Dict
C:L7:class PluginMetrics[L8:__init__,L18:record_event,L26:record_state_change,L29:record_restart,L32:set_uptime_start,L35:get_uptime]; L56:class MetricsCollector[L57:__init__,L60:get_or_create,L65:record_event,L68:record_state_change,L71:record_restart,L74:set_uptime_start]
F:L8:def __init__()->[]; L18:def record_event()->['time.time']; L26:def record_state_change()->[]; L29:def record_restart()->[]; L32:def set_uptime_start()->['time.time']; L35:def get_uptime()->['time.time']; L38:def get_stability_score()->['max', 'min']; L42:def to_dict()->['self.get_stability_score', 'self.get_uptime'] (+9 more)
N:-

## `runtime\observability\observability_hub.py`

I:L2:from eventbus import EventBus; L3:from runtime.event_types import Event; L4:from runtime.observability.event_store import EventStore; L5:from runtime.observability.metrics import MetricsCollector; L6:from runtime.observability.health_engine import HealthEngineV2
C:L8:class ObservabilityHub[L9:__init__,L18:_on_event,L24:_publish_metrics,L29:_publish_health,L37:record_plugin_state_change,L40:record_plugin_restart]
F:L9:def __init__()->['EventStore', 'HealthEngineV2', 'MetricsCollector', 'self._event_bus.subscribe']; L18:def _on_event()->['self._event_store.add', 'self._metrics.record_event', 'self._publish_health', 'self._publish_metrics']; L24:def _publish_metrics()->['self._event_bus.emit', 'self._metrics.get_plugin_metrics']; L29:def _publish_health()->['self._event_bus.emit', 'self._health_engine.get_detailed_health']; L37:def record_plugin_state_change()->['self._metrics.record_state_change']; L40:def record_plugin_restart()->['self._metrics.record_restart', 'self._publish_metrics']; L44:def record_plugin_uptime_start()->['self._metrics.set_uptime_start']; L47:def get_health_score()->['self._health_engine.calculate_score'] (+6 more)
N:-

## `runtime\observability\resource_monitor.py`

I:L1:import psutil; L2:import threading; L3:import time; L4:from typing import Dict; L4:from typing import Optional
C:L6:class ResourceMonitor[L7:__init__,L14:start,L22:stop,L28:_monitor_loop,L34:_collect_resources]
F:L7:def __init__()->['threading.Event']; L14:def start()->['self._stop_event.clear', 'self._thread.start', 'threading.Thread']; L22:def stop()->['self._stop_event.set', 'self._thread.join']; L28:def _monitor_loop()->['self._collect_resources', 'self._stop_event.wait']; L34:def _collect_resources()->['proc.cpu_percent', 'proc.memory_info', 'proc.num_threads', 'proc.oneshot']
N:-

## `runtime\recovery\boot_journal.py`

I:L2:import json; L3:import os; L4:import time; L5:from typing import Optional; L5:from typing import Dict; L5:from typing import Any
C:L7:class BootJournal[L8:__init__,L12:_ensure_dir,L17:load,L36:save,L48:mark_start,L55:mark_shutdown]
F:L8:def __init__()->['self._ensure_dir']; L12:def _ensure_dir()->['os.makedirs', 'os.path.dirname', 'os.path.exists']; L17:def load()->['json.load', 'open', 'os.path.exists']; L36:def save()->['json.dump', 'open', 'os.replace', 'print']; L48:def mark_start()->['self.load', 'self.save', 'time.time']; L55:def mark_shutdown()->['self.load', 'self.save', 'time.time']; L61:def was_crash()->['journal.get', 'self.load']; L65:def get_last_start()->['self.load', 'self.load().get'] (+1 more)
N:L26:open; L40:open

## `runtime\recovery\recovery_manager.py`

I:L2:import time; L3:from typing import Dict; L3:from typing import Any; L4:from runtime.recovery.boot_journal import BootJournal; L5:from runtime.recovery.report import RecoveryReport; L6:from runtime.state.storage import JsonStorage; L7:from runtime.state.migrations import migrate_snapshot; L8:from runtime.state.snapshot_engine import SnapshotEngine
C:L10:class RecoveryManager[L11:__init__,L17:is_crash_recovery,L20:perform_recovery,L43:get_recovery_status]
F:L11:def __init__()->['RecoveryReport']; L17:def is_crash_recovery()->['self.boot_journal.was_crash']; L20:def perform_recovery()->['JsonStorage', 'migrate_snapshot', 'plugin_states.items', 'self.boot_journal.get_last_start']; L43:def get_recovery_status()->['self.boot_journal.get_last_shutdown', 'self.boot_journal.get_last_start', 'self.is_crash_recovery', 'self.report.to_dict']
N:-

## `runtime\recovery\report.py`

I:L2:import time; L3:from typing import List; L3:from typing import Dict; L3:from typing import Any; L41:import json; L41:import os
C:L5:class RecoveryReport[L6:__init__,L14:set_crash,L18:set_snapshot,L21:add_restored,L24:add_skipped,L27:set_message]
F:L6:def __init__()->[]; L14:def set_crash()->[]; L18:def set_snapshot()->[]; L21:def add_restored()->['self.plugins_restored.append']; L24:def add_skipped()->['self.plugins_skipped.append']; L27:def set_message()->[]; L30:def to_dict()->[]; L40:def save()->['json.dump', 'open', 'os.makedirs', 'os.path.dirname']
N:L45:open

## `runtime\recovery\__init__.py`

I:L2:from runtime.recovery.boot_journal import BootJournal; L3:from runtime.recovery.recovery_manager import RecoveryManager; L4:from runtime.recovery.report import RecoveryReport
C:-
F:-
N:-

## `runtime\state\migrations.py`

I:L1:from typing import Dict; L1:from typing import Any
C:-
F:L3:def migrate_snapshot()->['snapshot.get']
N:-

## `runtime\state\snapshot_engine.py`

I:L2:import time; L3:from typing import Dict; L3:from typing import Any
C:L5:class SnapshotEngine[L8:__init__,L13:create_snapshot,L38:apply_snapshot,L56:_validate_snapshot]
F:L8:def __init__()->[]; L13:def create_snapshot()->['pm.get_plugin_names', 'pm.get_plugin_state', 'pm.get_quarantine_data', 'self.notification_manager.get_history']; L38:def apply_snapshot()->['data.get', 'print', 'self._validate_snapshot', 'self.runtime_controller._plugin_manager.restore_quarantine']; L56:def _validate_snapshot()->['isinstance']
N:-

## `runtime\state\state_manager.py`

I:L1:import threading; L2:import time; L3:from typing import Optional; L4:from runtime.state.storage import JsonStorage; L5:from runtime.state.snapshot_engine import SnapshotEngine; L6:from runtime.state.migrations import migrate_snapshot
C:L8:class StateManager[L9:__init__,L18:save_snapshot,L24:load_snapshot,L31:_autosave_loop,L36:start_autosave,L45:stop_autosave]
F:L9:def __init__()->['threading.Event', 'threading.Lock']; L18:def save_snapshot()->['print', 'self.snapshot_engine.create_snapshot', 'self.storage.save']; L24:def load_snapshot()->['migrate_snapshot', 'self.snapshot_engine.apply_snapshot', 'self.storage.load']; L31:def _autosave_loop()->['self._stop_event.wait', 'self.save_snapshot']; L36:def start_autosave()->['print', 'self._stop_event.clear', 'self._thread.start', 'threading.Thread']; L45:def stop_autosave()->['print', 'self._stop_event.set', 'self._thread.join', 'self.save_snapshot']
N:-

## `runtime\state\storage.py`

I:L1:import os; L2:import json; L3:import tempfile; L4:from typing import Optional; L4:from typing import Dict; L4:from typing import Any
C:L6:class JsonStorage[L7:__init__,L11:_ensure_dir,L16:save,L27:load,L37:clear]
F:L7:def __init__()->['self._ensure_dir']; L11:def _ensure_dir()->['os.makedirs', 'os.path.dirname', 'os.path.exists']; L16:def save()->['json.dump', 'open', 'os.replace', 'print']; L27:def load()->['json.load', 'open', 'os.path.exists', 'print']; L37:def clear()->['os.path.exists', 'os.remove']
N:L19:open; L31:open

## `runtime\state\__init__.py`

I:L1:from runtime.state.state_manager import StateManager; L2:from runtime.state.snapshot_engine import SnapshotEngine; L3:from runtime.state.storage import JsonStorage; L4:from runtime.state.migrations import migrate_snapshot
C:-
F:-
N:-

## `runtime\websocket\connection_manager.py`

I:L2:import threading; L3:from typing import Set
C:L5:class ConnectionManager[L6:__init__,L11:register,L16:unregister,L22:broadcast,L35:get_clients_count,L39:get_message_count]
F:L6:def __init__()->['set', 'threading.Lock']; L11:def register()->['len', 'print', 'self._connections.add']; L16:def unregister()->['len', 'print', 'self._connections.remove']; L22:def broadcast()->['client.send', 'disconnected.append', 'print', 'self.unregister']; L35:def get_clients_count()->['len']; L39:def get_message_count()->[]
N:-

## `runtime\websocket\event_serializer.py`

I:L2:import json; L3:from runtime.event_types import Event
C:-
F:L5:def serialize_event()->['hasattr', 'json.dumps']
N:-

## `runtime\websocket\websocket_hub.py`

I:L2:import json; L3:from runtime.websocket.connection_manager import ConnectionManager; L4:from runtime.websocket.event_serializer import serialize_event; L5:from runtime.event_types import Event
C:L7:class WebSocketHub[L8:__init__,L20:broadcast_notification,L27:_on_event,L36:_on_health_update,L49:_on_metrics_update,L62:get_stats]
F:L8:def __init__()->['ConnectionManager', 'print', 'self.event_bus.subscribe']; L20:def broadcast_notification()->['json.dumps', 'notification.to_dict', 'self.connection_manager.broadcast']; L27:def _on_event()->['self.connection_manager.broadcast', 'self.runtime_log.error', 'serialize_event']; L36:def _on_health_update()->['data.get', 'json.dumps', 'self.connection_manager.broadcast', 'self.runtime_log.error']; L49:def _on_metrics_update()->['data.get', 'json.dumps', 'self.connection_manager.broadcast', 'self.runtime_log.error']; L62:def get_stats()->['self.connection_manager.get_clients_count', 'self.connection_manager.get_message_count']; L68:def stop()->[]
N:-

## `runtime\notifications\channels\base_channel.py`

I:L2:from runtime.notifications.notification_types import Notification
C:L4:class BaseChannel[L5:send]
F:L5:def send()->[]
N:-

## `runtime\notifications\channels\dashboard_channel.py`

I:L2:import json; L3:from runtime.notifications.channels.base_channel import BaseChannel; L4:from runtime.notifications.notification_types import Notification
C:L6:class DashboardChannel(BaseChannel)[L7:__init__,L10:send]
F:L7:def __init__()->[]; L10:def send()->['self.websocket_hub.broadcast_notification']
N:-

## `runtime\notifications\channels\discord_channel.py`

I:L2:from datetime import datetime; L3:from runtime.http_client import HTTPClient; L3:from runtime.http_client import HTTPClientError; L4:from runtime.notifications.channels.base_channel import BaseChannel; L5:from runtime.notifications.notification_types import Notification
C:L7:class DiscordChannel(BaseChannel)[L8:__init__,L12:send]
F:L8:def __init__()->['HTTPClient']; L12:def send()->['datetime.utcnow', 'datetime.utcnow().isoformat', 'print', 'self.http_client.post']
N:-

## `runtime\notifications\channels\log_channel.py`

I:L2:from runtime.notifications.channels.base_channel import BaseChannel; L3:from runtime.notifications.notification_types import Notification
C:L5:class LogChannel(BaseChannel)[L6:__init__,L9:send]
F:L6:def __init__()->[]; L9:def send()->['notification.type.value.upper', 'self.runtime_log.error', 'self.runtime_log.info']
N:-

## `runtime\notifications\channels\__init__.py`

I:
C:-
F:-
N:-

## `runtime\migrations\versions\v1_to_v2_example.py`

I:L2:from typing import Any; L2:from typing import Dict; L3:from runtime.migrations.base import BaseMigration; L4:from runtime.migrations.registry import get_registry
C:L6:class ExportV1ToV2(BaseMigration)[L10:apply]
F:L10:def apply()->[]
N:-

## `plugins\execution\base.py`

I:L2:from abc import ABC; L2:from abc import abstractmethod
C:L4:class PluginExecutor(ABC)[L6:execute_event,L11:start,L16:stop]
F:L6:def execute_event()->[]; L11:def start()->[]; L16:def stop()->[]
N:L6:db

## `plugins\execution\executor_registry.py`

I:L2:from typing import Dict; L2:from typing import Type; L3:from plugins.execution.base import PluginExecutor; L4:from plugins.execution.inprocess_executor import InProcessExecutor; L5:from plugins.execution.subprocess_executor import SubprocessExecutor
C:L7:class ExecutorRegistry[L8:__init__,L11:register,L14:get,L17:get_default]
F:L22:def get_executor_registry()->['ExecutorRegistry', 'InProcessExecutor', 'SubprocessExecutor', '_registry.register']; L8:def __init__()->[]; L11:def register()->[]; L14:def get()->['self._executors.get']; L17:def get_default()->['self._executors.get']
N:-

## `plugins\execution\inprocess_executor.py`

I:L2:import time; L3:from plugins.execution.base import PluginExecutor
C:L5:class InProcessExecutor(PluginExecutor)[L6:execute_event,L20:start,L23:stop]
F:L6:def execute_event()->['hasattr', 'plugin.on_event', 'time.time']; L20:def start()->[]; L23:def stop()->[]
N:L6:db

## `plugins\execution\process_manager.py`

I:L2:import threading; L3:import time; L4:from enum import Enum; L5:from dataclasses import dataclass; L6:from typing import Dict; L6:from typing import Optional; L6:from typing import List; L7:from datetime import datetime
C:L9:class ProcessStatus(Enum)[]; L17:class ProcessInfo[]; L29:class ProcessManager[L30:__init__,L36:register,L47:update_heartbeat,L54:mark_crashed,L73:unregister,L78:get_process]; L98:class ProcessMonitor[L99:__init__,L108:start,L116:stop,L122:_monitor_loop]
F:L30:def __init__()->['threading.Lock']; L36:def register()->['ProcessInfo', 'time.time']; L47:def update_heartbeat()->['time.time']; L54:def mark_crashed()->['self._quarantine_callback']; L73:def unregister()->[]; L78:def get_process()->['self._processes.get']; L82:def get_all_processes()->['list', 'self._processes.values']; L86:def restart_process()->[] (+5 more)
N:-

## `plugins\execution\subprocess_executor.py`

I:L2:import multiprocessing; L3:import threading; L4:import time; L5:from plugins.execution.base import PluginExecutor; L6:from plugins.execution.process_manager import ProcessManager; L6:from plugins.execution.process_manager import ProcessMonitor; L30:from plugins.execution.worker import worker_main
C:L8:class SubprocessExecutor(PluginExecutor)[L9:__init__,L15:set_process_manager,L20:start,L23:stop,L26:start_plugin,L46:stop_plugin]
F:L9:def __init__()->[]; L15:def set_process_manager()->['ProcessMonitor', 'self._monitor.start']; L20:def start()->['self.start_plugin']; L23:def stop()->['self.stop_plugin']; L26:def start_plugin()->['multiprocessing.Process', 'multiprocessing.Queue', 'process.start', 'self._process_manager.register']; L46:def stop_plugin()->['self._process_manager.unregister', "worker['event_queue'].put", "worker['process'].is_alive", "worker['process'].join"]; L62:def execute_event()->['isinstance', 'self._process_manager.mark_crashed', 'self.start_plugin', 'self.stop_plugin']; L79:def _restart_plugin_process()->['self.stop_plugin_by_name'] (+1 more)
N:L62:db; L83:db

## `plugins\execution\worker.py`

I:L2:import sys; L3:import time; L4:import threading; L5:from importlib import import_module; L32:from plugins.plugin_base import PluginBase
C:-
F:L11:def send_heartbeat()->['_heartbeat_queue.put', 'time.sleep', 'time.time']; L21:def load_plugin()->['Exception', 'dir', 'getattr', 'import_module']; L44:def worker_main()->['_plugin.on_event', 'event_queue.get', 'heartbeat_thread.start', 'load_plugin']
N:-

## `plugins\execution\__init__.py`

I:L2:from plugins.execution.base import PluginExecutor; L3:from plugins.execution.inprocess_executor import InProcessExecutor; L4:from plugins.execution.subprocess_executor import SubprocessExecutor; L5:from plugins.execution.executor_registry import get_executor_registry; L5:from plugins.execution.executor_registry import ExecutorRegistry; L6:from plugins.execution.process_manager import ProcessManager; L6:from plugins.execution.process_manager import ProcessInfo; L6:from plugins.execution.process_manager import ProcessStatus; L6:from plugins.execution.process_manager import ProcessMonitor
C:-
F:-
N:-

## `FunPayAPI\common\enums.py`

I:L1:from __future__ import annotations; L2:from enum import Enum
C:L5:class EventTypes(Enum)[]; L34:class MessageTypes(Enum)[]; L88:class OrderStatuses(Enum)[]; L104:class SubCategoryTypes(Enum)[]; L114:class Currency(Enum)[L127:__str__,L137:code]; L147:class Wallet(Enum)[]
F:L127:def __str__()->[]; L137:def code()->['Exception']
N:-

## `FunPayAPI\common\exceptions.py`

I:L4:import requests; L5:from  import types
C:L8:class AccountNotInitiatedError(Exception)[L14:__init__,L17:__str__]; L21:class RequestFailedError(Exception)[L26:__init__,L39:short_str,L42:__str__]; L54:class UnauthorizedError(RequestFailedError)[L60:__init__,L63:short_str]; L67:class WithdrawError(RequestFailedError)[L72:__init__,L78:short_str]; L82:class RaiseError(RequestFailedError)[L87:__init__,L93:short_str]; L98:class ImageUploadError(RequestFailedError)[L103:__init__,L109:short_str]; L113:class MessageNotDeliveredError(RequestFailedError)[L118:__init__,L125:short_str]; L130:class FeedbackEditingError(RequestFailedError)[L136:__init__,L143:short_str]; L148:class LotParsingError(RequestFailedError)[L153:__init__,L160:short_str]; L165:class LotSavingError(RequestFailedError)[L170:__init__,L178:short_str]; L183:class RefundError(RequestFailedError)[L188:__init__,L195:short_str]
F:L14:def __init__()->[]; L17:def __str__()->[]; L26:def __init__()->[]; L39:def short_str()->[]; L42:def __str__()->['self.response.content.decode']; L60:def __init__()->['super', 'super(UnauthorizedError, self).__init__']; L63:def short_str()->[]; L72:def __init__()->['super', 'super(WithdrawError, self).__init__'] (+15 more)
N:-

## `FunPayAPI\common\utils.py`

I:L5:import string; L6:import random; L7:import re; L8:from datetime import datetime; L8:from datetime import timedelta; L8:from datetime import timezone; L10:from enums import Currency
C:L117:class RegularExpressions(object)[L124:__new__,L129:__init__]
F:L62:def random_tag()->["''.join", 'random.choice', 'range']; L71:def parse_wait_time()->["''.join", 'i.isdigit', 'int']; L90:def parse_currency()->['CURRENCY_MAP.get']; L93:def parse_funpay_datetime()->['any', 'date_text.count', 'date_text.split', "date_text.split(', ')[1].split"]; L124:def __new__()->['getattr', 'hasattr', 'setattr', 'super']; L129:def __init__()->['re.compile']
N:-

## `FunPayAPI\common\__init__.py`

I:
C:-
F:-
N:-

## `bot\handlers\ai_agent.py`

I:L1:from __future__ import annotations; L3:import logging; L4:from aiogram import Router; L4:from aiogram import F; L5:from aiogram.filters import Command; L6:from aiogram.types import CallbackQuery; L6:from aiogram.types import Message; L6:from aiogram.types import InlineKeyboardMarkup; L6:from aiogram.types import InlineKeyboardButton; L13:from bot.services import ai_agent_service
C:-
F:L20:def _confirm_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L31:def cb_ai_agent()->["'\\n'.join", '_get_ai_keyboard', 'ai_agent_service.is_ready', 'len']; L51:def _get_ai_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L66:def cb_ai_scan_files()->["'\\n'.join", '_get_ai_keyboard', 'ai_agent_service.scan_project_files', 'lines.append']; L83:def cmd_analyze()->["(message.text or '').split", 'Command', 'ai_agent_service.analyze_project', 'len']; L105:def cb_apply_patch()->['F.data.startswith', '_confirm_keyboard', 'query.answer', 'query.data.split']; L113:def cb_reject_patch()->['F.data.startswith', '_confirm_keyboard', 'query.answer', 'query.data.split']; L121:def cb_confirm_apply_patch()->['F.data.startswith', '_get_ai_keyboard', 'ai_agent_service.apply_patch', 'query.answer'] (+2 more)
N:-

## `bot\handlers\callbacks.py`

I:L1:from __future__ import annotations; L3:import json; L4:import logging; L5:import os; L6:import subprocess; L7:import time; L8:from typing import Any; L10:import psutil; L11:from aiogram import Router; L11:from aiogram import F; L12:from aiogram.types import CallbackQuery; L12:from aiogram.types import InlineKeyboardMarkup; L13:from aiogram.exceptions import TelegramBadRequest; L15:from bot.api_client import APIClient; L15:from bot.api_client import APIClientError; L16:from bot.config import get_bot_config; L17:from bot.services.cache_service import bot_cache; L18:from bot.formatters import format_balance; L18:from bot.formatters import format_report; L18:from bot.formatters import format_system_status
C:-
F:L54:def _is_local()->["(urlparse(cfg.hub_url).hostname or '').lower", 'get_bot_config', 'urlparse']; L62:def _healthcheck()->['api.get']; L70:def _get_hub_pid()->['any', 'proc.info.get', 'psutil.process_iter', 'str']; L81:def _safe_edit()->['len', 'logger.error', 'logger.warning', 'query.message.edit_text']; L101:def cb_back()->['_safe_edit', 'get_main_menu', 'router.callback_query']; L111:def cb_start_hub()->['_is_local', '_safe_edit', 'format_error', 'get_confirm_keyboard']; L125:def cb_stop_hub()->['_is_local', '_safe_edit', 'format_error', 'get_confirm_keyboard']; L139:def cb_confirm_start_hub()->['__import__', '_get_hub_pid', '_healthcheck', '_safe_edit'] (+32 more)
N:L55:urllib; L163:open; L163:subprocess; L206:urllib

## `bot\handlers\notifications.py`

I:L1:from __future__ import annotations; L3:import logging; L5:from aiogram import Router; L5:from aiogram import F; L6:from aiogram.types import CallbackQuery; L8:from bot.formatters import format_error; L9:from bot.keyboards.main import get_back_button
C:-
F:L17:def cb_notifications()->['get_back_button', 'logger.error', 'query.answer', 'query.message.edit_text']
N:-

## `bot\handlers\start.py`

I:L1:from __future__ import annotations; L3:import logging; L4:import os; L5:import json; L6:import bcrypt; L8:from aiogram import Router; L8:from aiogram import F; L9:from aiogram.filters import Command; L10:from aiogram.types import Message; L11:from aiogram.exceptions import TelegramBadRequest; L13:from bot.formatters import format_welcome; L14:from bot.keyboards.main import get_main_menu; L15:from bot.config import get_bot_config
C:-
F:L23:def cmd_start()->['Command', 'format_welcome', 'get_main_menu', 'message.answer']; L34:def cmd_ping()->['Command', 'message.reply', 'router.message']; L39:def cmd_auth()->["(message.text or '').strip", 'Command', 'bcrypt.checkpw', 'bcrypt.gensalt']
N:L57:open; L71:open; L81:open

## `bot\keyboards\main.py`

I:L1:from __future__ import annotations; L3:from aiogram.types import InlineKeyboardMarkup; L3:from aiogram.types import InlineKeyboardButton
C:-
F:L6:def get_main_menu()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L39:def get_lots_menu()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L56:def get_back_button()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L62:def get_logs_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup', 'rows.append']; L77:def get_plugins_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L93:def get_plugin_detail_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L105:def get_confirm_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L115:def get_refresh_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']
N:-

## `bot\keyboards\__init__.py`

I:L1:from bot.keyboards.main import get_main_menu; L1:from bot.keyboards.main import get_back_button; L1:from bot.keyboards.main import get_logs_keyboard; L1:from bot.keyboards.main import get_plugins_keyboard; L1:from bot.keyboards.main import get_plugin_detail_keyboard
C:-
F:-
N:-

## `bot\middlewares\auth.py`

I:L1:from __future__ import annotations; L3:import bcrypt; L4:import json; L5:import logging; L6:import os; L7:from typing import Any; L7:from typing import Awaitable; L7:from typing import Callable; L7:from typing import Dict; L9:from aiogram import BaseMiddleware; L10:from aiogram.types import CallbackQuery; L10:from aiogram.types import Message; L10:from aiogram.types import TelegramObject; L12:from bot.config import get_bot_config
C:L54:class AuthMiddleware(BaseMiddleware)[L55:__call__]
F:L23:def _load_authorized()->['json.load', 'open', 'os.path.exists']; L33:def _is_authorized()->['_load_authorized', 'data.get', 'get_bot_config', 'str']; L47:def _is_public_command()->['text.strip', 'text.strip().split', 'text.strip().split()[0].split', "text.strip().split()[0].split('@')[0].lower"]; L55:def __call__()->['_is_authorized', '_is_public_command', 'event.answer', 'handler']
N:L26:open

## `bot\middlewares\__init__.py`

I:L1:from bot.middlewares.auth import AuthMiddleware
C:-
F:-
N:-

## `bot\services\ai_agent_service.py`

I:L1:from __future__ import annotations; L3:import asyncio; L4:import json; L5:import logging; L6:import os; L7:import time; L8:from dataclasses import dataclass; L8:from dataclasses import field; L9:from datetime import datetime; L9:from datetime import timezone; L9:from datetime import timedelta; L10:from pathlib import Path; L11:from typing import Any; L11:from typing import Dict; L11:from typing import List; L11:from typing import Optional; L13:import aiohttp; L14:from aiogram.types import InlineKeyboardMarkup; L14:from aiogram.types import InlineKeyboardButton; L367:import base64
C:L20:class PatchProposal[]; L30:class AIAgentService[L31:__init__,L44:configure,L53:is_ready,L56:start,L67:stop,L76:_scanner_loop]
F:L31:def __init__()->['Path', "Path('.').resolve"]; L44:def configure()->[]; L53:def is_ready()->['bool']; L56:def start()->['asyncio.create_task', 'len', 'logger.info', 'logger.warning']; L67:def stop()->['logger.info', 'self._scan_task.cancel', 'self._scan_task.done']; L76:def _scanner_loop()->['asyncio.sleep', 'logger.error', 'self._scan_logs']; L89:def _scan_logs()->['any', 'errors.append', 'f.readlines', 'f.seek']; L113:def _analyze_errors()->['PatchProposal', 'analysis.get', 'int', 'logger.error'] (+11 more)
N:L64:asyncio; L85:asyncio; L93:open; L170:aiohttp; L171:aiohttp; L316:db

## `bot\services\cache_service.py`

I:L8:from __future__ import annotations; L10:import asyncio; L11:import logging; L12:import time; L13:from typing import Dict; L13:from typing import Tuple; L15:from bot.api_client import api_client
C:L20:class BotCache[L21:__init__,L27:register,L30:get,L45:refresh_all,L54:refresh_loop]
F:L21:def __init__()->['asyncio.Lock']; L27:def register()->[]; L30:def get()->['KeyError', 'api_client.get', 'self._cache.get', 'time.time']; L45:def refresh_all()->['api_client.get', 'list', 'logger.warning', 'self._paths.items']; L54:def refresh_loop()->['asyncio.sleep', 'self.refresh_all']
N:L56:asyncio

## `bot\services\__init__.py`

I:L1:from bot.services.ai_agent_service import ai_agent_service
C:-
F:-
N:-

# 5. FunPay API client layer

## `FunPayAPI\account.py`
I:L1:from __future__ import annotations; L3:import html; L4:from typing import TYPE_CHECKING; L4:from typing import Literal; L4:from typing import Any; L4:from typing import Optional; L4:from typing import IO; L6:import FunPayAPI.common.enums; L7:from FunPayAPI.common.utils import parse_currency; L7:from FunPayAPI.common.utils import RegularExpressions; L8:from types import PaymentMethod; L8:from types import CalcResult
C:L33:class Account[L53:__init__,L145:method,L233:get,L284:runner_request,L306:get_payload_data,L353:abuse_runner,L388:get_subcategory_public_lots,L482:get_my_subcategory_lots]
F:L53:def __init__()->['HTTPAdapter', 'Retry', 'requests.Session', 'self.session.mount']; L145:def method()->['exceptions.RequestFailedError', 'exceptions.UnauthorizedError', 'link.endswith', 'min']; L233:def get()->['BeautifulSoup', 'balance.replace', 'balance.text.rsplit', 'cookies.get']; L284:def runner_request()->['json.dumps', 'payload.get', 'self.method']; L306:def get_payload_data()->['msg_ids.get', 'objects.append', 'objects.extend', 'sorted']; L353:def abuse_runner()->['self.get_payload_data', 'self.runner.get_result', 'self.runner_request']; L388:def get_subcategory_public_lots()->["''.join", 'BeautifulSoup', 'amount.isdigit', 'attributes.get']; L482:def get_my_subcategory_lots()->['BeautifulSoup', 'amount.isdigit', 'bool', 'exceptions.AccountNotInitiatedError']; L538:def get_lot_page()->['BeautifulSoup', 'chat_header.find', "chat_header.find('div', class_='media-user-name').find", 'exceptions.AccountNotInitiatedError']; L595:def get_balance()->['BeautifulSoup', 'exceptions.AccountNotInitiatedError', 'exceptions.UnauthorizedError', 'float'] (+58 more)
N:L773:open

## `FunPayAPI\types.py`
I:L4:from __future__ import annotations; L6:import re; L7:from typing import Literal; L7:from typing import overload; L7:from typing import Optional; L9:import FunPayAPI.common.enums; L10:from common.utils import RegularExpressions; L11:from common.enums import MessageTypes; L11:from common.enums import OrderStatuses; L11:from common.enums import SubCategoryTypes; L11:from common.enums import Currency; L12:import datetime
C:L15:class BaseOrderInfo[L20:__init__]; L29:class ChatShortcut(BaseOrderInfo)[L52:__init__,L76:get_last_message_type,L123:__str__]; L127:class BuyerViewing[L132:__init__,L148:lot_id,L156:subcategory_type]; L165:class Chat[L188:__init__]; L204:class Message(BaseOrderInfo)[L236:__init__,L293:get_message_type,L342:__str__]; L346:class OrderShortcut(BaseOrderInfo)[L390:__init__,L422:parse_amount,L435:__str__]; L438:class Server[L439:__init__]; L443:class Side[L444:__init__]; L448:class Order[L506:__init__,L550:get_field,L562:get_field_value,L582:get_field_value_any,L601:short_description,L605:title,L609:full_description,L613:payment_msg]; L665:class Category[L679:__init__,L695:add_subcategory,L706:get_subcategory,L721:get_subcategories,L730:get_sorted_subcategories]; L740:class SubCategory[L757:__init__,L777:is_common,L781:is_lots,L785:is_currency,L789:is_chips,L793:ui_name,L796:telegram_text]; L803:class LotField[L804:__init__]; L810:class LotFields[L833:__init__,L878:amount,L890:amount,L894:public_link,L899:private_link,L904:fields,L913:edit_fields,L922:set_fields]; L972:class ChipOffer[L973:__init__,L983:key]; L988:class ChipFields[L989:__init__,L1005:fields,L1014:renew_fields,L1037:__parse_offers]; L1056:class LotPage[L1082:__init__,L1100:seller_url]; L1105:class SellerShortcut[L1110:__init__,L1126:link]; L1130:class LotShortcut[L1159:__init__]; L1199:class MyLotShortcut[L1228:__init__]; L1263:class UserProfile[L1286:__init__,L1308:get_lot,L1322:get_lots,L1332:get_sorted_lots,L1336:get_sorted_lots,L1340:get_sorted_lots,L1343:get_sorted_lots,L1366:update_lot]; L1410:class Review[L1448:__init__]; L1475:class Balance[L1495:__init__]; L1511:class PaymentMethod[L1514:__init__]; L1525:class CalcResult[L1528:__init__,L1546:get_coefficient,L1557:commission_coefficient,L1562:commission_percent]; L1566:class Wallet[L1569:__init__]
F:L20:def __init__()->[]; L52:def __init__()->['BaseOrderInfo.__init__', 'self.get_last_message_type']; L76:def get_last_message_type()->['RegularExpressions', 'res.DEAR_VENDORS.search', 'res.DISCORD.search', 'res.ORDER_ID.search']; L123:def __str__()->[]; L132:def __init__()->['bool']; L148:def lot_id()->['id_.isdigit', 'int', 'self.link.split']; L156:def subcategory_type()->[]; L188:def __init__()->[]; L236:def __init__()->['BaseOrderInfo.__init__', 'self.get_message_type']; L293:def get_message_type()->['RegularExpressions', 'res.DEAR_VENDORS.search', 'res.DISCORD.search', 'res.ORDER_ID.search'] (+73 more)
N:-

## `FunPayAPI\__init__.py`
I:L1:from account import Account; L2:from common import exceptions; L2:from common import utils; L2:from common import enums; L3:from  import types
C:-
F:-
N:-

## `FunPayAPI\common\enums.py`
I:L1:from __future__ import annotations; L2:from enum import Enum
C:L5:class EventTypes(Enum)[]; L34:class MessageTypes(Enum)[]; L88:class OrderStatuses(Enum)[]; L104:class SubCategoryTypes(Enum)[]; L114:class Currency(Enum)[L127:__str__,L137:code]; L147:class Wallet(Enum)[]
F:L127:def __str__()->[]; L137:def code()->['Exception']
N:-

## `FunPayAPI\common\exceptions.py`
I:L4:import requests; L5:from  import types
C:L8:class AccountNotInitiatedError(Exception)[L14:__init__,L17:__str__]; L21:class RequestFailedError(Exception)[L26:__init__,L39:short_str,L42:__str__]; L54:class UnauthorizedError(RequestFailedError)[L60:__init__,L63:short_str]; L67:class WithdrawError(RequestFailedError)[L72:__init__,L78:short_str]; L82:class RaiseError(RequestFailedError)[L87:__init__,L93:short_str]; L98:class ImageUploadError(RequestFailedError)[L103:__init__,L109:short_str]; L113:class MessageNotDeliveredError(RequestFailedError)[L118:__init__,L125:short_str]; L130:class FeedbackEditingError(RequestFailedError)[L136:__init__,L143:short_str]; L148:class LotParsingError(RequestFailedError)[L153:__init__,L160:short_str]; L165:class LotSavingError(RequestFailedError)[L170:__init__,L178:short_str]; L183:class RefundError(RequestFailedError)[L188:__init__,L195:short_str]
F:L14:def __init__()->[]; L17:def __str__()->[]; L26:def __init__()->[]; L39:def short_str()->[]; L42:def __str__()->['self.response.content.decode']; L60:def __init__()->['super', 'super(UnauthorizedError, self).__init__']; L63:def short_str()->[]; L72:def __init__()->['super', 'super(WithdrawError, self).__init__']; L78:def short_str()->[]; L87:def __init__()->['super', 'super(RaiseError, self).__init__'] (+13 more)
N:-

## `FunPayAPI\common\utils.py`
I:L5:import string; L6:import random; L7:import re; L8:from datetime import datetime; L8:from datetime import timedelta; L8:from datetime import timezone; L10:from enums import Currency
C:L117:class RegularExpressions(object)[L124:__new__,L129:__init__]
F:L62:def random_tag()->["''.join", 'random.choice', 'range']; L71:def parse_wait_time()->["''.join", 'i.isdigit', 'int']; L90:def parse_currency()->['CURRENCY_MAP.get']; L93:def parse_funpay_datetime()->['any', 'date_text.count', 'date_text.split', "date_text.split(', ')[1].split"]; L124:def __new__()->['getattr', 'hasattr', 'setattr', 'super']; L129:def __init__()->['re.compile']
N:-

## `FunPayAPI\common\__init__.py`
C:-
F:-
N:-

# 6. Telegram bot layer

## `bot\api_client.py`
I:L1:from __future__ import annotations; L3:import json; L4:import logging; L5:from typing import Any; L7:import aiohttp; L9:from bot.config import get_bot_config
C:L14:class APIClientError(Exception)[]; L18:class APIClient[L19:__init__,L26:_request,L48:get,L51:post]
F:L19:def __init__()->['get_bot_config', 'self._cfg.hub_url.rstrip']; L26:def _request()->['APIClientError', '__import__', "__import__('os').environ.get", 'aiohttp.ClientSession']; L48:def get()->['self._request']; L51:def post()->['self._request']
N:L30:aiohttp; L32:aiohttp; L38:aiohttp

## `bot\config.py`
I:L1:from __future__ import annotations; L3:import os; L4:from dataclasses import dataclass; L30:import json
C:L8:class BotConfig[]
F:L15:def get_bot_config()->['BotConfig', 'RuntimeError', 'cfg.get', "cfg.get('bot_token', '').strip"]; L52:def get_hub_url()->['os.environ.get', 'render_url.strip', 'url.strip']
N:L29:open

## `bot\formatters.py`
I:L1:from __future__ import annotations; L3:import datetime; L4:from html import escape; L5:from typing import Any
C:-
F:L8:def _text()->['escape', 'str']; L14:def _ts()->['datetime.datetime.fromtimestamp', 'datetime.datetime.now', 'dt.strftime']; L22:def _safe_float()->['float']; L29:def format_welcome()->["'\\n'.join"]; L44:def format_balance()->["'\\n'.join", '_safe_float', '_text', '_ts']; L91:def format_report()->["'\\n'.join", '_text', '_ts', 'data.get']; L131:def format_system_status()->["'\\n'.join", '_text', '_ts', 'health_data.get']; L180:def format_lots()->["'\\n'.join", '_safe_float', '_text', 'data.get']; L218:def format_lots_stats()->["'\\n'.join", '_MARKERS.items', 'by_supplier.items', 'by_supplier.setdefault']; L266:def format_simulation()->["'\\n'.join", '_text', '_ts', 'data.get'] (+15 more)
N:-

## `bot\__init__.py`
C:-
F:-
N:-

## `bot\handlers\ai_agent.py`
I:L1:from __future__ import annotations; L3:import logging; L4:from aiogram import Router; L4:from aiogram import F; L5:from aiogram.filters import Command; L6:from aiogram.types import CallbackQuery; L6:from aiogram.types import Message; L6:from aiogram.types import InlineKeyboardMarkup; L6:from aiogram.types import InlineKeyboardButton; L13:from bot.services import ai_agent_service
C:-
F:L20:def _confirm_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L31:def cb_ai_agent()->["'\\n'.join", '_get_ai_keyboard', 'ai_agent_service.is_ready', 'len']; L51:def _get_ai_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L66:def cb_ai_scan_files()->["'\\n'.join", '_get_ai_keyboard', 'ai_agent_service.scan_project_files', 'lines.append']; L83:def cmd_analyze()->["(message.text or '').split", 'Command', 'ai_agent_service.analyze_project', 'len']; L105:def cb_apply_patch()->['F.data.startswith', '_confirm_keyboard', 'query.answer', 'query.data.split']; L113:def cb_reject_patch()->['F.data.startswith', '_confirm_keyboard', 'query.answer', 'query.data.split']; L121:def cb_confirm_apply_patch()->['F.data.startswith', '_get_ai_keyboard', 'ai_agent_service.apply_patch', 'query.answer']; L130:def cb_confirm_reject_patch()->['F.data.startswith', '_get_ai_keyboard', 'ai_agent_service.reject_patch', 'query.answer']; L138:def cb_cancel()->['F.data.startswith', '_get_ai_keyboard', 'query.answer', 'query.message.edit_text']
N:-

## `bot\handlers\callbacks.py`
I:L1:from __future__ import annotations; L3:import json; L4:import logging; L5:import os; L6:import subprocess; L7:import time; L8:from typing import Any; L10:import psutil; L11:from aiogram import Router; L11:from aiogram import F; L12:from aiogram.types import CallbackQuery; L12:from aiogram.types import InlineKeyboardMarkup
C:-
F:L54:def _is_local()->["(urlparse(cfg.hub_url).hostname or '').lower", 'get_bot_config', 'urlparse']; L62:def _healthcheck()->['api.get']; L70:def _get_hub_pid()->['any', 'proc.info.get', 'psutil.process_iter', 'str']; L81:def _safe_edit()->['len', 'logger.error', 'logger.warning', 'query.message.edit_text']; L101:def cb_back()->['_safe_edit', 'get_main_menu', 'router.callback_query']; L111:def cb_start_hub()->['_is_local', '_safe_edit', 'format_error', 'get_confirm_keyboard']; L125:def cb_stop_hub()->['_is_local', '_safe_edit', 'format_error', 'get_confirm_keyboard']; L139:def cb_confirm_start_hub()->['__import__', '_get_hub_pid', '_healthcheck', '_safe_edit']; L182:def cb_confirm_stop_hub()->['_get_hub_pid', '_safe_edit', 'format_error', 'format_hub_stop']; L205:def _is_local()->["(urlparse(cfg.hub_url).hostname or '').lower", 'get_bot_config', 'urlparse'] (+30 more)
N:L55:urllib; L163:open; L163:subprocess; L206:urllib

## `bot\handlers\notifications.py`
I:L1:from __future__ import annotations; L3:import logging; L5:from aiogram import Router; L5:from aiogram import F; L6:from aiogram.types import CallbackQuery; L8:from bot.formatters import format_error; L9:from bot.keyboards.main import get_back_button
C:-
F:L17:def cb_notifications()->['get_back_button', 'logger.error', 'query.answer', 'query.message.edit_text']
N:-

## `bot\handlers\start.py`
I:L1:from __future__ import annotations; L3:import logging; L4:import os; L5:import json; L6:import bcrypt; L8:from aiogram import Router; L8:from aiogram import F; L9:from aiogram.filters import Command; L10:from aiogram.types import Message; L11:from aiogram.exceptions import TelegramBadRequest; L13:from bot.formatters import format_welcome; L14:from bot.keyboards.main import get_main_menu
C:-
F:L23:def cmd_start()->['Command', 'format_welcome', 'get_main_menu', 'message.answer']; L34:def cmd_ping()->['Command', 'message.reply', 'router.message']; L39:def cmd_auth()->["(message.text or '').strip", 'Command', 'bcrypt.checkpw', 'bcrypt.gensalt']
N:L57:open; L71:open; L81:open

## `bot\keyboards\main.py`
I:L1:from __future__ import annotations; L3:from aiogram.types import InlineKeyboardMarkup; L3:from aiogram.types import InlineKeyboardButton
C:-
F:L6:def get_main_menu()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L39:def get_lots_menu()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L56:def get_back_button()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L62:def get_logs_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup', 'rows.append']; L77:def get_plugins_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L93:def get_plugin_detail_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L105:def get_confirm_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L115:def get_refresh_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']
N:-

## `bot\keyboards\__init__.py`
I:L1:from bot.keyboards.main import get_main_menu; L1:from bot.keyboards.main import get_back_button; L1:from bot.keyboards.main import get_logs_keyboard; L1:from bot.keyboards.main import get_plugins_keyboard; L1:from bot.keyboards.main import get_plugin_detail_keyboard
C:-
F:-
N:-

## `bot\middlewares\auth.py`
I:L1:from __future__ import annotations; L3:import bcrypt; L4:import json; L5:import logging; L6:import os; L7:from typing import Any; L7:from typing import Awaitable; L7:from typing import Callable; L7:from typing import Dict; L9:from aiogram import BaseMiddleware; L10:from aiogram.types import CallbackQuery; L10:from aiogram.types import Message
C:L54:class AuthMiddleware(BaseMiddleware)[L55:__call__]
F:L23:def _load_authorized()->['json.load', 'open', 'os.path.exists']; L33:def _is_authorized()->['_load_authorized', 'data.get', 'get_bot_config', 'str']; L47:def _is_public_command()->['text.strip', 'text.strip().split', 'text.strip().split()[0].split', "text.strip().split()[0].split('@')[0].lower"]; L55:def __call__()->['_is_authorized', '_is_public_command', 'event.answer', 'handler']
N:L26:open

## `bot\middlewares\__init__.py`
I:L1:from bot.middlewares.auth import AuthMiddleware
C:-
F:-
N:-

## `bot\services\ai_agent_service.py`
I:L1:from __future__ import annotations; L3:import asyncio; L4:import json; L5:import logging; L6:import os; L7:import time; L8:from dataclasses import dataclass; L8:from dataclasses import field; L9:from datetime import datetime; L9:from datetime import timezone; L9:from datetime import timedelta; L10:from pathlib import Path
C:L20:class PatchProposal[]; L30:class AIAgentService[L31:__init__,L44:configure,L53:is_ready,L56:start,L67:stop,L76:_scanner_loop,L89:_scan_logs,L113:_analyze_errors]
F:L31:def __init__()->['Path', "Path('.').resolve"]; L44:def configure()->[]; L53:def is_ready()->['bool']; L56:def start()->['asyncio.create_task', 'len', 'logger.info', 'logger.warning']; L67:def stop()->['logger.info', 'self._scan_task.cancel', 'self._scan_task.done']; L76:def _scanner_loop()->['asyncio.sleep', 'logger.error', 'self._scan_logs']; L89:def _scan_logs()->['any', 'errors.append', 'f.readlines', 'f.seek']; L113:def _analyze_errors()->['PatchProposal', 'analysis.get', 'int', 'logger.error']; L131:def _call_llm_with_fallback()->['logger.error', 'logger.warning', 'provider.get', 'self._call_llm']; L143:def _call_llm()->["'\\n'.join", 'Exception', 'ValueError', 'aiohttp.ClientSession'] (+9 more)
N:L64:asyncio; L85:asyncio; L93:open; L170:aiohttp; L171:aiohttp; L316:db; L318:db; L341:db

## `bot\services\cache_service.py`
I:L8:from __future__ import annotations; L10:import asyncio; L11:import logging; L12:import time; L13:from typing import Dict; L13:from typing import Tuple; L15:from bot.api_client import api_client
C:L20:class BotCache[L21:__init__,L27:register,L30:get,L45:refresh_all,L54:refresh_loop]
F:L21:def __init__()->['asyncio.Lock']; L27:def register()->[]; L30:def get()->['KeyError', 'api_client.get', 'self._cache.get', 'time.time']; L45:def refresh_all()->['api_client.get', 'list', 'logger.warning', 'self._paths.items']; L54:def refresh_loop()->['asyncio.sleep', 'self.refresh_all']
N:L56:asyncio

## `bot\services\__init__.py`
I:L1:from bot.services.ai_agent_service import ai_agent_service
C:-
F:-
N:-

# 7. Database layer

## `runtime\database\base.py`
I:L6:import os; L7:import threading; L8:from pathlib import Path; L9:from sqlalchemy import create_engine; L9:from sqlalchemy import event; L10:from sqlalchemy.orm import sessionmaker; L10:from sqlalchemy.orm import scoped_session; L10:from sqlalchemy.orm import declarative_base; L78:from runtime.database.models import User; L78:from runtime.database.models import Order; L78:from runtime.database.models import Product; L78:from runtime.database.models import Lot
C:-
F:L19:def _resolve_db_path()->['Path', 'Path(__file__).resolve', 'abs_path.as_posix', 'abs_path.parent.mkdir']; L31:def get_engine()->['_resolve_db_path', 'create_engine', 'cursor.close', 'cursor.execute']; L62:def get_session()->['_session_factory', 'get_engine', 'scoped_session', 'sessionmaker']; L75:def init_db()->['Base.metadata.create_all', 'get_engine']; L86:def shutdown_db()->['_engine.dispose', '_session_factory.remove']; L53:def _set_sqlite_pragma()->['cursor.close', 'cursor.execute', 'db_url.startswith', 'dbapi_connection.cursor']
N:L56:db; L57:db; L70:db

## `runtime\database\ledger.py`
I:L20:import time; L21:from decimal import Decimal; L22:from typing import Optional; L22:from typing import List; L22:from typing import Dict; L22:from typing import Any; L23:from sqlalchemy import func; L25:from runtime.database.base import get_session; L26:from runtime.database.models import Transaction; L26:from runtime.database.models import Order; L26:from runtime.database.models import Provider
C:L29:class Ledger[L35:record,L88:record_order_income,L102:record_provider_payment,L118:record_commission,L132:record_refund,L146:record_profit,L160:record_deposit,L174:get_order_transactions]
F:L35:def record()->['Transaction', 'get_session', 'session.add', 'session.close']; L88:def record_order_income()->['Ledger.record', 'abs']; L102:def record_provider_payment()->['Ledger.record', 'abs']; L118:def record_commission()->['Ledger.record', 'abs']; L132:def record_refund()->['Ledger.record', 'abs']; L146:def record_profit()->['Ledger.record']; L160:def record_deposit()->['Ledger.record', 'abs']; L174:def get_order_transactions()->['get_session', 'session.close', 'session.query', 'session.query(Transaction).filter']; L188:def get_order_profit()->['float', 'func.sum', 'get_session', 'session.close']; L202:def get_balance_snapshot()->['float', 'func.sum', 'get_session', 'query.filter'] (+2 more)
N:L54:db; L63:db; L78:db; L79:db; L82:db; L179:db; L193:db; L213:db

## `runtime\database\models.py`
I:L16:import time; L17:from sqlalchemy import Column; L17:from sqlalchemy import Integer; L17:from sqlalchemy import String; L17:from sqlalchemy import Float; L17:from sqlalchemy import BigInteger; L17:from sqlalchemy import Text; L17:from sqlalchemy import DateTime; L17:from sqlalchemy import ForeignKey; L17:from sqlalchemy import Enum; L17:from sqlalchemy import JSON; L17:from sqlalchemy import Boolean
C:L30:class OrderStatus(str,enum.Enum)[]; L39:class TransactionType(str,enum.Enum)[]; L49:class ProviderStatus(str,enum.Enum)[]; L56:class LotStatus(str,enum.Enum)[]; L65:class User(Base)[L77:__repr__]; L81:class Product(Base)[L98:__repr__]; L102:class Lot(Base)[L119:__repr__]; L123:class Provider(Base)[L139:__repr__]; L143:class Order(Base)[L174:__repr__]; L182:class Transaction(Base)[L200:__repr__]; L208:class Review(Base)[L224:__repr__]; L228:class Log(Base)[]; L245:class ProviderBalance(Base)[]
F:L77:def __repr__()->[]; L98:def __repr__()->[]; L119:def __repr__()->[]; L139:def __repr__()->[]; L174:def __repr__()->[]; L200:def __repr__()->[]; L224:def __repr__()->[]
N:-

## `runtime\database\repository.py`
I:L7:import time; L8:from typing import Optional; L8:from typing import List; L8:from typing import Dict; L8:from typing import Any; L9:from sqlalchemy import func; L11:from runtime.database.base import get_session; L12:from runtime.database.models import User; L12:from runtime.database.models import Order; L12:from runtime.database.models import Product; L12:from runtime.database.models import Lot; L12:from runtime.database.models import Provider
C:L19:class Repository[L25:get_or_create_user,L67:create_order,L99:get_order,L109:get_order_by_id,L117:update_order_status,L143:get_active_orders,L157:get_orders_by_status,L171:count_orders]
F:L25:def get_or_create_user()->['User', 'get_session', 'session.add', 'session.close']; L67:def create_order()->['Order', 'get_session', 'session.add', 'session.close']; L99:def get_order()->['get_session', 'session.close', 'session.query', 'session.query(Order).filter']; L109:def get_order_by_id()->['get_session', 'session.close', 'session.query', 'session.query(Order).get']; L117:def update_order_status()->['extra.items', 'get_session', 'hasattr', 'session.close']; L143:def get_active_orders()->['Order.status.in_', 'get_session', 'session.close', 'session.query']; L157:def get_orders_by_status()->['Order.started_at.desc', 'get_session', 'session.close', 'session.query']; L171:def count_orders()->['func.count', 'get_session', 'session.close', 'session.query']; L185:def create_lot()->['Lot', 'get_session', 'session.add', 'session.close']; L214:def get_lot()->['get_session', 'session.close', 'session.query', 'session.query(Lot).filter'] (+6 more)
N:L34:db; L38:db; L47:db; L48:db; L56:db; L59:db; L89:db; L90:db

## `runtime\database\__init__.py`
I:L11:from runtime.database.base import get_engine; L11:from runtime.database.base import get_session; L11:from runtime.database.base import init_db; L11:from runtime.database.base import shutdown_db; L11:from runtime.database.base import Base; L18:from runtime.database.models import User; L18:from runtime.database.models import Order; L18:from runtime.database.models import Product; L18:from runtime.database.models import Lot; L18:from runtime.database.models import Provider; L18:from runtime.database.models import Transaction; L18:from runtime.database.models import Review
C:-
F:-
N:-

# 8. Plugin system

## `plugins\autobump_plugin.py`
I:L18:import time; L19:import threading; L20:import json; L21:from datetime import datetime; L21:from datetime import timedelta; L22:from collections import deque; L23:from pathlib import Path; L25:from plugins.plugin_base import PluginBase; L26:from runtime.http_client import HTTPClient; L26:from runtime.http_client import HTTPClientError; L129:from bot.config import get_hub_url; L344:import datetime
C:L42:class AutoBumpPlugin(PluginBase)[L126:__init__,L145:on_load,L149:on_enable,L158:on_disable,L164:on_unload,L167:on_error,L173:_loop,L192:_run_once]
F:L367:def get_plugin_stats()->['hasattr', 'p.get_stats', 'plugin_manager.plugins.get']; L126:def __init__()->['HTTPClient', 'deque', 'get_hub_url', 'super']; L145:def on_load()->['json.dumps', 'self._log', 'self.load_config']; L149:def on_enable()->['self._log', 'self._stop_event.clear', 'self._thread.is_alive', 'self._thread.start']; L158:def on_disable()->['self._log', 'self._stop_event.set', 'self._thread.is_alive', 'self._thread.join']; L164:def on_unload()->['self.on_disable']; L167:def on_error()->['self._log']; L173:def _loop()->['int', 'max', 'range', 'self._log']; L192:def _run_once()->['datetime.now', 'datetime.now().isoformat', 'int', 'self._bump_category']; L248:def _get_target_categories()->['cats.add', 'data.get', 'int', 'isinstance'] (+6 more)
N:-

## `plugins\autodonate_plugin.py`
I:L5:import time; L6:import re; L7:import threading; L8:from pathlib import Path; L9:from plugins.plugin_base import PluginBase; L10:from runtime.http_client import HTTPClient; L10:from runtime.http_client import HTTPClientError; L11:from runtime.order_tracker import get_supplier_order_registry; L128:from bot.config import get_hub_url; L499:from runtime.seller_service import seller_service_singleton
C:L89:class AutoDonatePlugin(PluginBase)[L125:__init__,L140:on_enable,L143:on_disable,L146:on_unload,L149:on_load,L164:on_event,L183:_on_new_order,L247:_on_new_message]
F:L125:def __init__()->['HTTPClient', 'get_hub_url', 'self._get_data_dir', 'super']; L140:def on_enable()->['self._start_replenish_timer']; L143:def on_disable()->['self._stop_replenish_timer']; L146:def on_unload()->['self._stop_replenish_timer']; L149:def on_load()->['env_mapping.items', 'self.config.get', "self.config.get('suppliers', {}).get", 'self.get_secret']; L164:def on_event()->['event.get', 'getattr', 'isinstance', 'self._on_new_message']; L183:def _on_new_order()->['DEFAULT_CONFIG.get', 'auto_resp.get', "auto_resp.get('discord_boost_received', DEFAULT_CONFIG['auto_responses']['discord_boost_received']).format", "auto_resp.get('game_rental_received', DEFAULT_CONFIG['auto_responses']['game_rental_received']).format"]; L247:def _on_new_message()->['any', 'auto_resp.get', 'event.get', 'getattr']; L266:def _on_order_completed()->['auto_resp.get', 'event.get', 'getattr', 'isinstance']; L287:def _on_review_received()->['event.get', 'getattr', 'int', 'isinstance'] (+27 more)
N:-

## `plugins\autosmm_plugin.py`
I:L5:import os; L6:import time; L7:import threading; L8:import json; L9:import re; L10:from collections import deque; L11:from pathlib import Path; L12:from urllib.parse import urlparse; L14:from plugins.plugin_base import PluginBase; L15:from runtime.http_client import HTTPClient; L15:from runtime.http_client import HTTPClientError; L16:from runtime.order_tracker import get_supplier_order_registry
C:L89:class AutoSMMPlugin(PluginBase)[L148:__init__,L179:_get_chat_lock,L189:on_load,L197:on_enable,L207:on_disable,L214:on_unload,L217:on_error,L225:_loop]
F:L148:def __init__()->['ExpiringDict', 'HTTPClient', 'TTLSet', 'deque']; L179:def _get_chat_lock()->['threading.Lock']; L189:def on_load()->['self._log', 'self.config.get', 'self.get_secret', 'self.load_config']; L197:def on_enable()->['self._log', 'self._stop.clear', 'self._worker.is_alive', 'self._worker.start']; L207:def on_disable()->['self._log', 'self._save_active_orders', 'self._stop.set', 'self._worker.is_alive']; L214:def on_unload()->['self.on_disable']; L217:def on_error()->['self._log', 'str']; L225:def _loop()->['int', 'max', 'range', 'self._check_active_orders']; L246:def _check_active_orders()->["','.join", "(status_obj.get('status') or '').strip", 'data.items', 'int']; L301:def _on_order_completed()->['chat_lock_registry.release', 'order_data.get', 'self._active.pop', 'self._log'] (+48 more)
N:L12:urllib; L879:open; L901:open

## `plugins\config_manager.py`
I:L2:import os; L3:import json; L4:from typing import Dict; L4:from typing import Any
C:-
F:L9:def get_config_path()->['os.makedirs', 'os.path.exists', 'os.path.join']; L15:def load_raw_config()->['get_config_path', 'json.load', 'open', 'os.path.exists']; L26:def create_default_config()->['get_config_path', 'json.dump', 'open', 'os.path.exists']; L41:def load_plugin_config()->['create_default_config', 'full_config.items', 'get_config_path', 'load_raw_config']; L52:def save_plugin_config()->['get_config_path', 'json.dump', 'open', 'print']
N:L19:open; L34:open; L60:open

## `plugins\dependency_manager.py`
I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Set; L2:from typing import Optional; L2:from typing import Tuple; L3:from collections import deque
C:L5:class DependencyError(Exception)[]; L8:class CircularDependencyError(DependencyError)[]; L11:class MissingDependencyError(DependencyError)[]; L14:class DependencyGraph[L15:__init__,L21:add_plugin,L36:remove_plugin,L54:validate_dependencies,L62:detect_circular,L85:topological_sort,L103:get_hard_dependents,L106:get_soft_dependents]
F:L15:def __init__()->[]; L21:def add_plugin()->['self.hard_reverse[dep].add', 'self.soft_reverse[opt].add', 'set']; L36:def remove_plugin()->['deps.discard', 'self.hard_reverse.values', 'self.hard_reverse[dep].discard', 'self.soft_reverse.values']; L54:def validate_dependencies()->['MissingDependencyError', 'missing.update', 'self.graph.items', 'set']; L62:def detect_circular()->['cycles.append', 'dfs', 'path.index', 'self.graph.get']; L85:def topological_sort()->['CircularDependencyError', 'deque', 'in_degree.items', 'len']; L103:def get_hard_dependents()->['self.hard_reverse.get', 'set']; L106:def get_soft_dependents()->['self.soft_reverse.get', 'set']; L109:def get_dependents()->['self.get_hard_dependents', 'self.get_soft_dependents']; L112:def can_disable()->['blockers.append', 'len', 'self.get_hard_dependents'] (+2 more)
N:-

## `plugins\health_score.py`
I:L2:import time; L3:from collections import deque; L4:from typing import Optional
C:L6:class PluginHealthScore[L7:__init__,L15:update_latency,L18:update_error,L21:update_restart,L24:update_event_count,L27:tick,L31:calculate_score]
F:L7:def __init__()->['deque']; L15:def update_latency()->['self._latency_history.append']; L18:def update_error()->['self._error_history.append']; L21:def update_restart()->['self._restart_history.append']; L24:def update_event_count()->['self._event_history.append']; L27:def tick()->[]; L31:def calculate_score()->['int', 'len', 'max', 'min']
N:-

## `plugins\loader.py`
I:L2:import os; L3:import sys; L4:import importlib; L5:import inspect; L6:from typing import Dict; L8:from plugins.plugin_base import PluginBase
C:-
F:L10:def discover_plugins()->['filename.endswith', 'filename.startswith', 'os.listdir', 'os.path.exists']; L22:def load_plugin()->['importlib.import_module', 'inspect.getmembers', 'issubclass', 'plugin_manager.register']; L35:def load_plugins()->['discover_plugins', 'len', 'load_plugin', 'plugin_manager.finalize_registration']; L52:def reload_plugin_config()->['plugin_manager.reload_plugin_config', 'print']
N:-

## `plugins\logger_plugin.py`
I:L2:from plugins.plugin_base import PluginBase
C:L4:class LoggerPlugin(PluginBase)[L17:on_init,L20:on_load,L24:on_enable,L27:on_disable,L30:on_error,L33:on_unload,L36:on_event]
F:L17:def on_init()->['print']; L20:def on_load()->['print', 'self.PLUGIN_INFO.get', 'self.load_config']; L24:def on_enable()->['print']; L27:def on_disable()->['print']; L30:def on_error()->['print']; L33:def on_unload()->['print']; L36:def on_event()->['len', 'print', 'self.config.get']
N:-

## `plugins\plugin_base.py`
I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Optional; L2:from typing import Any; L3:from plugins.config_manager import load_plugin_config; L3:from plugins.config_manager import save_plugin_config; L4:from security.secrets_manager import SecretsManager
C:L6:class PluginBase[L18:__init__,L27:get_info,L30:get_dependencies,L33:get_optional_dependencies,L36:on_load,L39:on_enable,L42:on_disable,L45:on_event]
F:L18:def __init__()->['SecretsManager']; L27:def get_info()->['self.__class__.PLUGIN_INFO.copy']; L30:def get_dependencies()->['self.PLUGIN_INFO.get']; L33:def get_optional_dependencies()->['self.PLUGIN_INFO.get']; L36:def on_load()->[]; L39:def on_enable()->[]; L42:def on_disable()->[]; L45:def on_event()->[]; L48:def on_error()->[]; L51:def on_unload()->[] (+13 more)
N:-

## `plugins\plugin_manager.py`
I:L2:import threading; L3:import time; L4:from typing import Dict; L4:from typing import Type; L4:from typing import List; L4:from typing import Optional; L5:from collections import deque; L7:from plugins.plugin_base import PluginBase; L8:from plugins.plugin_state import PluginState; L8:from plugins.plugin_state import PluginStateMachine; L8:from plugins.plugin_state import PluginErrorContext; L9:from plugins.plugin_registry import PluginRegistry
C:L14:class PluginManager[L15:__init__,L36:set_event_bus,L39:_get_fsm,L42:_transition,L83:register,L107:finalize_registration,L138:_start_watchdog,L145:_watchdog_loop]
F:L15:def __init__()->['DependencyGraph', 'PluginRegistry', 'get_executor_registry', 'threading.Event']; L36:def set_event_bus()->[]; L39:def _get_fsm()->['self._fsm.get']; L42:def _transition()->['PluginErrorContext', 'error_context.to_string', 'fsm.apply_transition', 'fsm.can_transition']; L83:def register()->['PluginHealthScore', 'PluginStateMachine', 'callable', 'getattr']; L107:def finalize_registration()->['Exception', 'any', 'info.get', 'plugin.PLUGIN_INFO.get']; L138:def _start_watchdog()->['print', 'self._stop_watchdog.clear', 'self._watchdog_thread.is_alive', 'self._watchdog_thread.start']; L145:def _watchdog_loop()->['self._check_plugin_health', 'self._stop_watchdog.wait']; L149:def _check_plugin_health()->['Event', 'fsm.get_state', 'hs.calculate_score', 'self._fsm.items']; L176:def quarantine_plugin()->['Event', 'print', 'self._get_fsm', 'self._get_fsm(name).get_state'] (+23 more)
N:L317:db

## `plugins\plugin_registry.py`
I:L2:from typing import Dict; L2:from typing import List; L2:from typing import Optional; L3:from plugins.plugin_state import PluginState
C:L6:class PluginRegistry[L12:__init__,L17:register_metadata,L32:update_state,L44:get_plugin,L58:get_all_plugins,L61:get_plugins_count,L64:get_plugin_state,L67:plugin_exists]
F:L12:def __init__()->[]; L17:def register_metadata()->['metadata.get', 'print']; L32:def update_state()->['print', 'self._errors.pop']; L44:def get_plugin()->['self._errors.get', 'self._states.get']; L58:def get_all_plugins()->['self._metadata.keys', 'self.get_plugin']; L61:def get_plugins_count()->['len']; L64:def get_plugin_state()->['self._states.get']; L67:def plugin_exists()->[]
N:-

## `plugins\plugin_state.py`
I:L2:from enum import Enum; L3:from typing import Dict; L3:from typing import Set; L3:from typing import Optional; L4:from dataclasses import dataclass
C:L7:class PluginState(Enum)[]; L27:class PluginErrorContext[L31:to_string]; L37:class PluginStateMachine[L38:__init__,L43:get_state,L46:get_state_name,L49:get_error_context,L52:get_error_message,L55:can_transition,L58:apply_transition]
F:L31:def to_string()->[]; L38:def __init__()->[]; L43:def get_state()->[]; L46:def get_state_name()->[]; L49:def get_error_context()->[]; L52:def get_error_message()->['self._error_context.to_string']; L55:def can_transition()->['ALLOWED_TRANSITIONS.get', 'set']; L58:def apply_transition()->['print', 'self.can_transition']
N:-

## `plugins\stars_plugin.py`
I:L1:import os; L2:import re; L3:import time; L4:import json; L5:from pathlib import Path; L6:from typing import Optional; L6:from typing import Dict; L6:from typing import Any; L7:from plugins.plugin_base import PluginBase; L8:from runtime.http_client import HTTPClient; L8:from runtime.http_client import HTTPClientError; L9:from runtime.order_tracker import get_tracker
C:L28:class StarsPlugin(PluginBase)[L45:__init__,L53:on_load,L58:on_event,L69:_on_new_stars_order,L117:_create_stars_order,L157:_check_stars_status,L178:_parse_stars,L185:_get_buyer_username]
F:L45:def __init__()->['HTTPClient', 'get_hub_url', 'self._get_data_dir', 'super']; L53:def on_load()->['self._log', 'self.load_config']; L58:def on_event()->['event.get', 'getattr', 'isinstance', 'self._on_new_stars_order']; L69:def _on_new_stars_order()->["DEFAULT_CONFIG['msg_completed'].format", "DEFAULT_CONFIG['msg_error'].format", "DEFAULT_CONFIG['msg_order_created'].format", 'fragment_order.get']; L117:def _create_stars_order()->['ValueError', 'int', 'isinstance', 'response.get']; L157:def _check_stars_status()->['response.get', 'self.http_client.get']; L178:def _parse_stars()->['int', 'match.group', 're.search']; L185:def _get_buyer_username()->['buyer.strip', 'getattr', 'isinstance', 'order_data.get']; L200:def _send_message()->['self._log', 'self.http_client.post']; L212:def _register_order_in_tracker()->['get_tracker', 'self._log', 'time.time'] (+3 more)
N:-

## `plugins\telegram_notifier_plugin.py`
I:L5:import time; L6:import threading; L7:import json; L8:import os; L9:from typing import Any; L9:from typing import Optional; L9:from typing import Dict; L9:from typing import List; L10:from plugins.plugin_base import PluginBase; L11:from runtime.http_client import HTTPClient; L11:from runtime.http_client import HTTPClientError; L57:from bot.config import get_hub_url
C:L35:class TelegramNotifierPlugin(PluginBase)[L54:__init__,L65:on_load,L72:on_enable,L83:on_disable,L86:on_unload,L93:on_event,L124:_send_telegram,L154:_answer_callback]
F:L54:def __init__()->['HTTPClient', 'get_hub_url', 'super', 'super().__init__']; L65:def on_load()->['self.config.get', 'self.get_secret', "self.get_secret('TELEGRAM_NOTIFIER_BOT_TOKEN', '').strip", "self.get_secret('TELEGRAM_NOTIFIER_CHAT_ID', '').strip"]; L72:def on_enable()->['os.environ.get', "os.environ.get('TELEGRAM_BOT_TOKEN', '').strip", 'self._log', 'self._start_polling']; L83:def on_disable()->['self._stop_polling']; L86:def on_unload()->['self._stop_polling']; L93:def on_event()->['event.get', 'getattr', 'isinstance', 'self._send_telegram']; L124:def _send_telegram()->['data.get', 'int', 'json.dumps', 'self._log']; L154:def _answer_callback()->['self.config.get', "self.config.get('bot_token', '').strip", 'self.http_client.post']; L169:def _edit_message()->['json.dumps', 'self.config.get', "self.config.get('bot_token', '').strip", 'self.http_client.post']; L191:def _start_polling()->['self._log'] (+16 more)
N:-

## `plugins\execution\base.py`
I:L2:from abc import ABC; L2:from abc import abstractmethod
C:L4:class PluginExecutor(ABC)[L6:execute_event,L11:start,L16:stop]
F:L6:def execute_event()->[]; L11:def start()->[]; L16:def stop()->[]
N:L6:db

## `plugins\execution\executor_registry.py`
I:L2:from typing import Dict; L2:from typing import Type; L3:from plugins.execution.base import PluginExecutor; L4:from plugins.execution.inprocess_executor import InProcessExecutor; L5:from plugins.execution.subprocess_executor import SubprocessExecutor
C:L7:class ExecutorRegistry[L8:__init__,L11:register,L14:get,L17:get_default]
F:L22:def get_executor_registry()->['ExecutorRegistry', 'InProcessExecutor', 'SubprocessExecutor', '_registry.register']; L8:def __init__()->[]; L11:def register()->[]; L14:def get()->['self._executors.get']; L17:def get_default()->['self._executors.get']
N:-

## `plugins\execution\inprocess_executor.py`
I:L2:import time; L3:from plugins.execution.base import PluginExecutor
C:L5:class InProcessExecutor(PluginExecutor)[L6:execute_event,L20:start,L23:stop]
F:L6:def execute_event()->['hasattr', 'plugin.on_event', 'time.time']; L20:def start()->[]; L23:def stop()->[]
N:L6:db

## `plugins\execution\process_manager.py`
I:L2:import threading; L3:import time; L4:from enum import Enum; L5:from dataclasses import dataclass; L6:from typing import Dict; L6:from typing import Optional; L6:from typing import List; L7:from datetime import datetime
C:L9:class ProcessStatus(Enum)[]; L17:class ProcessInfo[]; L29:class ProcessManager[L30:__init__,L36:register,L47:update_heartbeat,L54:mark_crashed,L73:unregister,L78:get_process,L82:get_all_processes,L86:restart_process]; L98:class ProcessMonitor[L99:__init__,L108:start,L116:stop,L122:_monitor_loop]
F:L30:def __init__()->['threading.Lock']; L36:def register()->['ProcessInfo', 'time.time']; L47:def update_heartbeat()->['time.time']; L54:def mark_crashed()->['self._quarantine_callback']; L73:def unregister()->[]; L78:def get_process()->['self._processes.get']; L82:def get_all_processes()->['list', 'self._processes.values']; L86:def restart_process()->[]; L93:def stop_process()->[]; L99:def __init__()->['threading.Event'] (+3 more)
N:-

## `plugins\execution\subprocess_executor.py`
I:L2:import multiprocessing; L3:import threading; L4:import time; L5:from plugins.execution.base import PluginExecutor; L6:from plugins.execution.process_manager import ProcessManager; L6:from plugins.execution.process_manager import ProcessMonitor; L30:from plugins.execution.worker import worker_main
C:L8:class SubprocessExecutor(PluginExecutor)[L9:__init__,L15:set_process_manager,L20:start,L23:stop,L26:start_plugin,L46:stop_plugin,L62:execute_event,L79:_restart_plugin_process]
F:L9:def __init__()->[]; L15:def set_process_manager()->['ProcessMonitor', 'self._monitor.start']; L20:def start()->['self.start_plugin']; L23:def stop()->['self.stop_plugin']; L26:def start_plugin()->['multiprocessing.Process', 'multiprocessing.Queue', 'process.start', 'self._process_manager.register']; L46:def stop_plugin()->['self._process_manager.unregister', "worker['event_queue'].put", "worker['process'].is_alive", "worker['process'].join"]; L62:def execute_event()->['isinstance', 'self._process_manager.mark_crashed', 'self.start_plugin', 'self.stop_plugin']; L79:def _restart_plugin_process()->['self.stop_plugin_by_name']; L85:def stop_plugin_by_name()->['self._process_manager.unregister', "worker['event_queue'].put", "worker['process'].is_alive", "worker['process'].join"]
N:L62:db; L83:db

## `plugins\execution\worker.py`
I:L2:import sys; L3:import time; L4:import threading; L5:from importlib import import_module; L32:from plugins.plugin_base import PluginBase
C:-
F:L11:def send_heartbeat()->['_heartbeat_queue.put', 'time.sleep', 'time.time']; L21:def load_plugin()->['Exception', 'dir', 'getattr', 'import_module']; L44:def worker_main()->['_plugin.on_event', 'event_queue.get', 'heartbeat_thread.start', 'load_plugin']
N:-

## `plugins\execution\__init__.py`
I:L2:from plugins.execution.base import PluginExecutor; L3:from plugins.execution.inprocess_executor import InProcessExecutor; L4:from plugins.execution.subprocess_executor import SubprocessExecutor; L5:from plugins.execution.executor_registry import get_executor_registry; L5:from plugins.execution.executor_registry import ExecutorRegistry; L6:from plugins.execution.process_manager import ProcessManager; L6:from plugins.execution.process_manager import ProcessInfo; L6:from plugins.execution.process_manager import ProcessStatus; L6:from plugins.execution.process_manager import ProcessMonitor
C:-
F:-
N:-

# 9. AI layer

## `funpayhub_main.py`
I:L1:import sys; L1:import os; L1:import io; L2:from datetime import datetime; L33:import sys; L34:import os; L35:import threading; L36:import time; L37:import logging; L38:import signal; L39:from pathlib import Path; L82:from flask import Flask
C:L12:class _Tee[L13:__init__,L15:write,L22:flush,L26:isatty]
F:L131:def _health()->['app.route']; L135:def _api_version()->['app.route']; L154:def _require_api_token()->['_req.headers.get', 'logger.warning', 'logging.getLogger', 'path.startswith']; L186:def _is_headless()->['os.environ.get', "os.environ.get('FUNPAYHUB_HEADLESS', '').strip", 'sys.platform.startswith']; L207:def _handle_sigterm()->['_shutdown_event.set', 'print']; L214:def run_flask()->['app.run']; L217:def main()->['HTTPClient', '_probe_client.get', '_shutdown_event.is_set', '_shutdown_event.wait']; L13:def __init__()->[]; L15:def write()->['s.flush', 's.write']; L22:def flush()->['s.flush'] (+1 more)
N:L8:open; L9:file_write; L15:file_write; L18:file_write; L268:open

## `runtime\ai_engineer_agent.py`
I:L9:import os; L10:import re; L11:import time; L12:import json; L13:import threading; L14:import logging; L15:from pathlib import Path; L16:from typing import Optional; L16:from typing import List; L16:from typing import Dict; L16:from typing import Any; L17:from datetime import datetime
C:L22:class AIEngineerAgent[L32:__init__,L48:start,L55:stop,L62:_start_scanner,L73:_scan_logs,L97:_analyze_errors,L106:_simple_fix_suggestion,L137:_propose_patch]
F:L32:def __init__()->['Path', 'os.environ.get', 'threading.Event']; L48:def start()->['logger.info', 'logger.warning', 'self._start_scanner']; L55:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L62:def _start_scanner()->['logger.error', 'self._scan_logs', 'self._stop.is_set', 'self._worker.start']; L73:def _scan_logs()->['any', 'errors.append', 'f.readlines', 'f.seek']; L97:def _analyze_errors()->["'\\n'.join", 'self._propose_patch', 'self._simple_fix_suggestion']; L106:def _simple_fix_suggestion()->['suggestions.items']; L137:def _propose_patch()->['int', 'self._pending_patches.append', 'self._send_admin', 'time.time']; L161:def apply_patch()->['logger.info', 'self._send_admin']; L173:def _send_admin()->['HTTPClient', 'hc.post', 'logger.error', 'os.environ.get'] (+1 more)
N:L78:open

## `runtime\ai_team_orchestrator.py`
I:L1:import json; L2:import os; L3:import re; L4:import subprocess; L5:import time; L6:from datetime import datetime; L7:from pathlib import Path; L8:from typing import Any; L8:from typing import Dict; L8:from typing import List; L8:from typing import Optional
C:L11:class LogMonitor[L12:__init__,L16:collect_errors,L26:_scan_file]; L44:class TaskManager[L45:__init__,L50:_load_tasks,L62:_save_tasks,L66:create_task,L85:_get_context]; L89:class AITeamOrchestrator[L90:__init__,L95:run_once,L108:_apply_safe_fix]
F:L12:def __init__()->['Path']; L16:def collect_errors()->['issues.extend', 'root.exists', 'root.is_dir', 'root.rglob']; L26:def _scan_file()->['any', 'enumerate', 'issues.append', 'line.strip']; L45:def __init__()->['Path', 'self.tasks_file.parent.mkdir']; L50:def _load_tasks()->['isinstance', 'json.load', 'open', 'self.tasks_file.exists']; L62:def _save_tasks()->['json.dump', 'open']; L66:def create_task()->['datetime.now', 'datetime.now().isoformat', 'datetime.now().timestamp', 'error_data.get']; L85:def _get_context()->[]; L90:def __init__()->['LogMonitor', 'TaskManager', 'object']; L95:def run_once()->['len', 'self._apply_safe_fix', 'self.log_monitor.collect_errors', 'self.task_manager.create_task'] (+1 more)
N:L29:open; L54:open; L63:open; L116:open; L117:file_write

## `tests\test_ai_team_integration.py`
I:L2:import json; L3:import pytest; L4:from unittest.mock import patch; L6:from runtime.ai_team.model_manager import AIModelManager; L7:from runtime.ai_team.scheduled_tasks import ScheduledTasks; L8:from runtime.ai_team.ai_team_orchestrator import AITeamOrchestrator
C:-
F:L12:def _mock_secrets_and_http()->['monkeypatch.setattr', 'pytest.fixture']; L32:def test_model_manager_initialization()->['AIModelManager']; L38:def test_model_manager_query_uses_primary_model()->['AIModelManager', 'manager.query']; L44:def test_scheduled_tasks_market_analysis()->['AIModelManager', 'ScheduledTasks', 'tasks.market_analysis']; L52:def test_scheduled_tasks_daily_report()->['AIModelManager', 'ScheduledTasks', 'tasks.generate_daily_report']; L60:def test_orchestrator_analyzes_errors_with_ai()->['AITeamOrchestrator', 'json.dumps', 'monkeypatch.setattr', 'orchestrator.analyze_error']; L15:def mock_get_secret()->[]; L26:def fake_post()->[]; L61:def fake_post_json()->['json.dumps']
N:-

## `runtime\ai_team\ai_team_orchestrator.py`
I:L1:import json; L2:import logging; L3:import re; L4:import threading; L5:import time; L6:from typing import Any; L6:from typing import Dict; L6:from typing import Optional; L8:from runtime.ai_team.model_manager import AIModelManager
C:L13:class AITeamOrchestrator[L14:__init__,L21:_load_config,L30:analyze_error,L59:run_24_7]
F:L14:def __init__()->['AIModelManager', 'self._load_config']; L21:def _load_config()->['isinstance', 'json.load', 'logger.warning', 'open']; L30:def analyze_error()->['isinstance', 'json.loads', 'json_match.group', 'logger.warning']; L59:def run_24_7()->['self.config.get', "self.config.get('schedule', {}).get", 'time.sleep']
N:L23:open

## `runtime\ai_team\model_manager.py`
I:L8:import json; L9:import logging; L10:from pathlib import Path; L11:from typing import Any; L11:from typing import Dict; L11:from typing import Optional; L13:from runtime.http_client import HTTPClient; L13:from runtime.http_client import HTTPClientError; L14:from security.secrets_manager import SecretsManager; L75:import time
C:L26:class AIModelManager[L27:__init__,L33:_load_config,L42:_resolve_api_key,L58:query,L97:_query_groq,L126:_query_google,L149:_query_openrouter]
F:L27:def __init__()->['HTTPClient', 'SecretsManager', 'self._load_config', 'self.config.get']; L33:def _load_config()->['json.load', 'logger.error', 'open']; L42:def _resolve_api_key()->['_ENV_KEYS.get', 'model_cfg.get', 'self.models.get', 'self.secrets.get_secret']; L58:def query()->['logger.error', 'logger.warning', 'range', 'self._query_google']; L97:def _query_groq()->['logger.warning', 'messages.append', 'model_config.get', 'self._resolve_api_key']; L126:def _query_google()->['logger.warning', 'model_config.get', 'self._resolve_api_key', 'self.http_client.post']; L149:def _query_openrouter()->['logger.warning', 'messages.append', 'model_config.get', 'self._resolve_api_key']
N:L36:open

## `runtime\ai_team\scheduled_tasks.py`
I:L4:import logging; L5:from datetime import datetime; L6:from typing import Any; L6:from typing import Dict
C:L11:class ScheduledTasks[L12:__init__,L16:market_analysis,L34:code_review,L55:generate_daily_report]
F:L12:def __init__()->['model_manager.config.get']; L16:def market_analysis()->['datetime.now', 'datetime.now().isoformat', 'self.model_manager.query']; L34:def code_review()->['datetime.now', 'datetime.now().isoformat', 'self.model_manager.query']; L55:def generate_daily_report()->['datetime.now', 'datetime.now().isoformat', 'datetime.now().strftime', 'self.model_manager.query']
N:-

## `runtime\ai_team\__init__.py`
I:L1:from runtime.ai_team.ai_team_orchestrator import AITeamOrchestrator; L2:from runtime.ai_team.model_manager import AIModelManager; L3:from runtime.ai_team.scheduled_tasks import ScheduledTasks
C:-
F:-
N:-

## `bot\handlers\ai_agent.py`
I:L1:from __future__ import annotations; L3:import logging; L4:from aiogram import Router; L4:from aiogram import F; L5:from aiogram.filters import Command; L6:from aiogram.types import CallbackQuery; L6:from aiogram.types import Message; L6:from aiogram.types import InlineKeyboardMarkup; L6:from aiogram.types import InlineKeyboardButton; L13:from bot.services import ai_agent_service
C:-
F:L20:def _confirm_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L31:def cb_ai_agent()->["'\\n'.join", '_get_ai_keyboard', 'ai_agent_service.is_ready', 'len']; L51:def _get_ai_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L66:def cb_ai_scan_files()->["'\\n'.join", '_get_ai_keyboard', 'ai_agent_service.scan_project_files', 'lines.append']; L83:def cmd_analyze()->["(message.text or '').split", 'Command', 'ai_agent_service.analyze_project', 'len']; L105:def cb_apply_patch()->['F.data.startswith', '_confirm_keyboard', 'query.answer', 'query.data.split']; L113:def cb_reject_patch()->['F.data.startswith', '_confirm_keyboard', 'query.answer', 'query.data.split']; L121:def cb_confirm_apply_patch()->['F.data.startswith', '_get_ai_keyboard', 'ai_agent_service.apply_patch', 'query.answer']; L130:def cb_confirm_reject_patch()->['F.data.startswith', '_get_ai_keyboard', 'ai_agent_service.reject_patch', 'query.answer']; L138:def cb_cancel()->['F.data.startswith', '_get_ai_keyboard', 'query.answer', 'query.message.edit_text']
N:-

## `bot\keyboards\main.py`
I:L1:from __future__ import annotations; L3:from aiogram.types import InlineKeyboardMarkup; L3:from aiogram.types import InlineKeyboardButton
C:-
F:L6:def get_main_menu()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L39:def get_lots_menu()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L56:def get_back_button()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L62:def get_logs_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup', 'rows.append']; L77:def get_plugins_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L93:def get_plugin_detail_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L105:def get_confirm_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']; L115:def get_refresh_keyboard()->['InlineKeyboardButton', 'InlineKeyboardMarkup']
N:-

## `bot\services\ai_agent_service.py`
I:L1:from __future__ import annotations; L3:import asyncio; L4:import json; L5:import logging; L6:import os; L7:import time; L8:from dataclasses import dataclass; L8:from dataclasses import field; L9:from datetime import datetime; L9:from datetime import timezone; L9:from datetime import timedelta; L10:from pathlib import Path
C:L20:class PatchProposal[]; L30:class AIAgentService[L31:__init__,L44:configure,L53:is_ready,L56:start,L67:stop,L76:_scanner_loop,L89:_scan_logs,L113:_analyze_errors]
F:L31:def __init__()->['Path', "Path('.').resolve"]; L44:def configure()->[]; L53:def is_ready()->['bool']; L56:def start()->['asyncio.create_task', 'len', 'logger.info', 'logger.warning']; L67:def stop()->['logger.info', 'self._scan_task.cancel', 'self._scan_task.done']; L76:def _scanner_loop()->['asyncio.sleep', 'logger.error', 'self._scan_logs']; L89:def _scan_logs()->['any', 'errors.append', 'f.readlines', 'f.seek']; L113:def _analyze_errors()->['PatchProposal', 'analysis.get', 'int', 'logger.error']; L131:def _call_llm_with_fallback()->['logger.error', 'logger.warning', 'provider.get', 'self._call_llm']; L143:def _call_llm()->["'\\n'.join", 'Exception', 'ValueError', 'aiohttp.ClientSession'] (+9 more)
N:L64:asyncio; L85:asyncio; L93:open; L170:aiohttp; L171:aiohttp; L316:db; L318:db; L341:db

# 10. EventBus

## `eventbus.py`
I:L2:import threading; L3:from typing import Dict; L3:from typing import List; L3:from typing import Callable; L3:from typing import Any; L4:from collections import defaultdict
C:L7:class EventBus[L10:__init__,L14:subscribe,L19:unsubscribe,L24:emit,L36:publish]
F:L10:def __init__()->['defaultdict', 'threading.Lock']; L14:def subscribe()->['self._listeners[event_type].append']; L19:def unsubscribe()->['self._listeners[event_type].remove']; L24:def emit()->['handler', 'print', 'self._listeners.get', 'self._listeners.get(event_type, []).copy']; L36:def publish()->['self.emit']
N:-

## `runtime\event_bus.py`
I:L2:import time; L3:import uuid; L4:from dataclasses import dataclass; L4:from dataclasses import field; L5:from enum import Enum
C:L8:class EventAction(Enum)[]; L19:class EventResult(Enum)[]; L26:class EventSource(Enum)[]; L33:class EventSeverity(Enum)[]; L40:class Event[L52:__post_init__,L61:to_dict]
F:L52:def __post_init__()->[]; L61:def to_dict()->[]
N:-

## `runtime\event_types.py`
I:L2:import time; L3:import uuid; L4:from dataclasses import dataclass; L4:from dataclasses import field; L5:from enum import Enum
C:L8:class EventAction(Enum)[]; L19:class EventResult(Enum)[]; L26:class EventSource(Enum)[]; L33:class EventSeverity(Enum)[]; L40:class Event[L52:__post_init__,L61:to_dict]
F:L52:def __post_init__()->[]; L61:def to_dict()->[]
N:-

# 11. Caching

## `runtime\ttl_cache.py`
I:L1:import threading; L2:import time; L3:from collections import deque
C:L6:class TTLSet[L7:__init__,L13:add,L20:__contains__,L26:discard,L30:_cleanup]
F:L7:def __init__()->['deque', 'threading.Lock']; L13:def add()->['self._cleanup', 'self._queue.append', 'time.time']; L20:def __contains__()->['self._cleanup', 'time.time']; L26:def discard()->['self._data.pop']; L30:def _cleanup()->['self._data.pop', 'self._queue.popleft']
N:-

## `runtime\cache\cache_manager.py`
I:L8:from __future__ import annotations; L10:import time; L11:from threading import RLock
C:L14:class CacheManager[L17:__init__,L22:get,L33:set,L38:invalidate,L42:clear,L46:snapshot]
F:L17:def __init__()->['RLock']; L22:def get()->['self._store.get', 'self._store.pop', 'time.time']; L33:def set()->['time.time']; L38:def invalidate()->['self._store.pop']; L42:def clear()->['self._store.clear']; L46:def snapshot()->['dict']
N:-

## `runtime\cache\__init__.py`
C:-
F:-
N:-

## `bot\services\cache_service.py`
I:L8:from __future__ import annotations; L10:import asyncio; L11:import logging; L12:import time; L13:from typing import Dict; L13:from typing import Tuple; L15:from bot.api_client import api_client
C:L20:class BotCache[L21:__init__,L27:register,L30:get,L45:refresh_all,L54:refresh_loop]
F:L21:def __init__()->['asyncio.Lock']; L27:def register()->[]; L30:def get()->['KeyError', 'api_client.get', 'self._cache.get', 'time.time']; L45:def refresh_all()->['api_client.get', 'list', 'logger.warning', 'self._paths.items']; L54:def refresh_loop()->['asyncio.sleep', 'self.refresh_all']
N:L56:asyncio

# 12. OrderFlow

## `runtime\order_flow.py`
I:L18:import time; L19:import threading; L20:import logging; L21:from typing import Optional; L21:from typing import Dict; L21:from typing import Any; L22:from pathlib import Path; L166:from runtime.http_client import HTTPClient; L167:from bot.config import get_hub_url; L183:from runtime.http_client import HTTPClient; L184:from bot.config import get_hub_url; L460:from runtime.plugin_markers import parse_marker
C:L27:class OrderFlowManager[L30:__init__,L48:start,L57:stop,L64:_on_new_order,L115:_on_order_cancelled,L136:_handle_low_balance,L157:_check_supplier_balance,L180:_deactivate_supplier_lots]
F:L30:def __init__()->['threading.Event', 'threading.RLock']; L48:def start()->['logger.info', 'self._eb.subscribe', 'self._start_worker']; L57:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L64:def _on_new_order()->['event.get', 'getattr', 'isinstance', 'logger.error']; L115:def _on_order_cancelled()->['event.get', 'getattr', 'isinstance', 'logger.error']; L136:def _handle_low_balance()->['logger.warning', 'order.get', 'self._deactivate_supplier_lots', 'self._orders.get']; L157:def _check_supplier_balance()->['HTTPClient', 'data.get', 'entry.get', 'float']; L180:def _deactivate_supplier_lots()->['HTTPClient', 'get_hub_url', 'hc.post']; L193:def _send_greeting()->['self._orders.get', 'self._send_to_chat']; L212:def _on_new_message()->["(event.get('text') or '').strip", 'event.get', 'getattr', 'isinstance'] (+20 more)
N:L561:db

## `runtime\order_tracker.py`
I:L7:import json; L8:import time; L9:import threading; L10:from runtime.http_client import HTTPClient; L11:from pathlib import Path; L12:from typing import Optional; L12:from typing import Dict; L12:from typing import Any; L18:import sys; L18:import os; L160:from pathlib import Path; L315:from runtime.database.repository import Repository
C:L34:class OrderPaymentTracker[L35:__init__,L45:start,L51:stop,L56:_start_worker,L84:_process_action,L122:_send_timeout_warning,L134:_do_refund,L158:_load_template]; L262:class SupplierOrderRegistry[L270:__init__,L284:is_registered,L295:get_supplier_order_id,L303:register,L325:remove,L335:_load,L345:_save]
F:L17:def _project_root()->['Path', 'Path(__file__).resolve', 'Path(sys.executable).resolve', 'getattr']; L24:def _tg_config()->['_project_root', 'cfg_path.exists', 'cfg_path.read_text', 'json.loads']; L246:def get_tracker()->['OrderPaymentTracker', '_tracker_singleton.start']; L359:def get_supplier_order_registry()->['SupplierOrderRegistry']; L35:def __init__()->['_tg_config', '_tg_config().get', 'threading.Event', 'threading.RLock']; L45:def start()->['self._start_worker', 'self.event_bus.subscribe']; L51:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L56:def _start_worker()->['print', 'self._process_action', 'self._stop.is_set', 'self._worker.start']; L84:def _process_action()->['data.get', 'self._do_refund', 'self._send_tg', 'self._send_timeout_warning']; L122:def _send_timeout_warning()->['self._load_template', 'self.svc.send_chat_message', 'tmpl.format'] (+14 more)
N:-

# 13. EmergencyManager

## `runtime\emergency_manager.py`
I:L18:import time; L19:import logging; L20:import threading; L21:from typing import Optional; L21:from typing import Set; L224:import os; L172:from runtime.http_client import HTTPClient; L173:from bot.config import get_hub_url; L184:from runtime.http_client import HTTPClient; L185:from bot.config import get_hub_url; L196:from runtime.http_client import HTTPClient; L197:from bot.config import get_hub_url
C:L26:class EmergencyManager[L35:__init__,L63:state,L67:is_normal,L71:is_emergency,L74:start,L78:stop,L83:check_supplier,L112:check_cancel_rate]
F:L35:def __init__()->['getattr', 'set', 'threading.RLock', 'time.time']; L63:def state()->[]; L67:def is_normal()->[]; L71:def is_emergency()->[]; L74:def start()->['logger.info']; L78:def stop()->['logger.info']; L83:def check_supplier()->['self._deactivate_supplier', 'self._error_counts.get', 'self._paused_suppliers.add', 'self._paused_suppliers.discard']; L112:def check_cancel_rate()->['max', 'self.emergency_stop']; L125:def emergency_stop()->['self._deactivate_all_lots', 'self._notify_admin', 'self._set_state']; L137:def resume()->['self._activate_all_lots', 'self._error_counts.clear', 'self._paused_suppliers.clear', 'self._set_state'] (+7 more)
N:-

# 14. ReportEngine

## `runtime\report_engine.py`
I:L9:import time; L10:import threading; L11:import logging; L12:from datetime import datetime; L12:from datetime import timezone; L12:from datetime import timedelta; L13:from typing import Optional; L13:from typing import Dict; L13:from typing import Any; L99:from runtime.database.ledger import Ledger; L132:from runtime.database.repository import Repository; L133:from runtime.database.ledger import Ledger
C:L21:class ReportEngine[L24:__init__,L30:start,L35:stop,L42:_start_scheduler,L63:send_daily_report,L72:send_evening_summary,L88:send_report_on_demand,L96:_build_daily_report]
F:L24:def __init__()->['threading.Event']; L30:def start()->['logger.info', 'self._start_scheduler']; L35:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L42:def _start_scheduler()->['datetime.now', 'logger.error', 'self._stop.is_set', 'self._worker.start']; L63:def send_daily_report()->['logger.info', 'self._build_daily_report', 'self._send_admin', 'time.time']; L72:def send_evening_summary()->['logger.info', 'self._build_daily_report', 'self._build_forecast', 'self._send_admin']; L88:def send_report_on_demand()->['self._build_daily_report', 'time.time']; L96:def _build_daily_report()->["'\\n'.join", 'Ledger.get_daily_report', 'abs', 'by_type.items']; L129:def _build_forecast()->["'\\n'.join", 'Ledger.get_daily_report', 'func.count', 'get_session']; L181:def _get_main_menu_markup()->[] (+2 more)
N:L150:db; L155:db; L157:db

# 15. Lot management

## `runtime\lot_generator.py`
I:L5:import os; L6:import json; L7:import random; L8:import itertools; L9:from pathlib import Path; L10:from typing import List; L10:from typing import Dict; L10:from typing import Any; L10:from typing import Optional; L11:import logging; L475:import os; L37:from runtime.database.base import get_session
C:L15:class LotGenerator[L16:__init__,L32:_calculate_copies,L54:_calculate_market_price,L82:_load_return_policy,L91:_load_synonyms,L101:_load_emojis,L111:_load_twiboost_services,L123:_load_kosell_products]
F:L16:def __init__()->['Path', 'self._load_emojis', 'self._load_return_policy', 'self._load_synonyms']; L32:def _calculate_copies()->['Order.status.in_', 'get_session', 'reversed', 'session.close']; L54:def _calculate_market_price()->['float', 'getattr', 'isinstance', 'l.get']; L82:def _load_return_policy()->['Path', 'policy_path.exists', 'policy_path.read_text', "policy_path.read_text(encoding='utf-8').strip"]; L91:def _load_synonyms()->['Path', 'data.get', 'isinstance', 'json.loads']; L101:def _load_emojis()->['Path', 'isinstance', 'json.loads', 'path.exists']; L111:def _load_twiboost_services()->['data.get', 'isinstance', 'json.loads', 'self._cache_path.exists']; L123:def _load_kosell_products()->[]; L133:def _categorize_service()->["(service.get('category') or '').lower", "(service.get('name') or '').lower", 'service.get']; L149:def _mutate_title()->["' '.join", 'enumerate', 'len', 'random.choice'] (+8 more)
N:L41:db

## `runtime\lot_matcher.py`
I:L23:from __future__ import annotations; L24:import re; L25:from difflib import SequenceMatcher; L26:from typing import List; L26:from typing import Dict; L26:from typing import Optional
C:-
F:L33:def _normalize()->['re.sub', "re.sub('\\\\s+', ' ', t).strip", 'text.lower']; L42:def _extract_quantities()->["(m.group(2) or '').lower", '_QTY_RE.finditer', 'int', 'm.group']; L58:def _text_similarity()->['SequenceMatcher', 'SequenceMatcher(None, _normalize(a), _normalize(b)).ratio', '_normalize']; L64:def match_lot_to_service()->["(s.get('type') or '').lower", 'LOT_GROUPS.items', 'SERVICE_TYPE_MAP.get', '_extract_quantities']; L226:def classify_match()->[]; L234:def auto_build_mapping()->['len', 'lot.get', 'match_lot_to_service', 'out_skipped.append']
N:-

# 16. Wallet / Payment

## `runtime\supplier_registry.py`
I:L1:import os; L2:import json; L3:from typing import Dict; L3:from typing import List; L3:from typing import Optional; L4:from runtime.http_client import HTTPClient
C:L6:class SupplierRegistry[L60:get_all_suppliers,L65:get_supplier,L70:get_enabled_suppliers,L75:get_api_key,L97:is_enabled,L111:get_marker]
F:L60:def get_all_suppliers()->[]; L65:def get_supplier()->['cls.SUPPLIERS.get']; L70:def get_enabled_suppliers()->['cfg.get', 'cls.SUPPLIERS.items']; L75:def get_api_key()->['cls.get_supplier', 'os.getenv', 'supplier.get']; L97:def is_enabled()->['cls.get_api_key', 'cls.get_supplier', 'supplier.get']; L111:def get_marker()->['cls.get_supplier', 'supplier.get']
N:-

## `runtime\supplier_worker.py`
I:L8:import time; L9:import queue; L10:import threading; L11:import logging; L12:from typing import Dict; L12:from typing import List; L12:from typing import Callable; L12:from typing import Optional
C:L17:class SupplierWorker[L20:__init__,L27:start,L31:stop,L35:submit,L40:active,L43:_run]; L59:class SupplierWorkerPool[L62:__init__,L65:get_worker,L72:submit,L77:stop_all,L82:active_workers]
F:L20:def __init__()->['queue.Queue', 'threading.Event', 'threading.Thread']; L27:def start()->['logger.debug', 'self._thread.start']; L31:def stop()->['self._stop.set']; L35:def submit()->['self._queue.put']; L40:def active()->[]; L43:def _run()->['callback', 'logger.error', 'self._queue.get', 'self._queue.task_done']; L62:def __init__()->[]; L65:def get_worker()->['SupplierWorker', 'self._workers[supplier].start']; L72:def submit()->['self.get_worker', 'worker.submit']; L77:def stop_all()->['self._workers.values', 'w.stop'] (+1 more)
N:-

# 17. Background jobs

## `plugins\health_score.py`
I:L2:import time; L3:from collections import deque; L4:from typing import Optional
C:L6:class PluginHealthScore[L7:__init__,L15:update_latency,L18:update_error,L21:update_restart,L24:update_event_count,L27:tick,L31:calculate_score]
F:L7:def __init__()->['deque']; L15:def update_latency()->['self._latency_history.append']; L18:def update_error()->['self._error_history.append']; L21:def update_restart()->['self._restart_history.append']; L24:def update_event_count()->['self._event_history.append']; L27:def tick()->[]; L31:def calculate_score()->['int', 'len', 'max', 'min']
N:-

## `runtime\price_monitor.py`
I:L4:import time; L5:from pathlib import Path
C:-
F:L7:def auto_adjust_prices()->['l.get', 'len', 'lot.get', 'my_lots.get']
N:-

## `web\health.py`
C:-
F:-
N:-

## `runtime\backup\scheduler.py`
I:L2:import threading; L3:import time; L4:from typing import Optional; L5:from runtime.backup.backup_manager import BackupManager
C:L8:class BackupScheduler[L9:__init__,L17:start,L26:stop,L33:_loop,L39:_create_backup_and_rotate,L48:_rotate_backups]
F:L9:def __init__()->['threading.Event']; L17:def start()->['print', 'self._stop_event.clear', 'self._thread.start', 'threading.Thread']; L26:def stop()->['print', 'self._stop_event.set', 'self._thread.join']; L33:def _loop()->['self._create_backup_and_rotate', 'self._stop_event.wait']; L39:def _create_backup_and_rotate()->['print', 'self._rotate_backups', 'self.backup_manager.create_backup']; L48:def _rotate_backups()->['len', 'print', 'self.backup_manager.delete_backup', 'self.backup_manager.list_backups']
N:-

## `runtime\observability\health_engine.py`
I:L2:from runtime.observability.metrics import MetricsCollector; L3:from runtime.observability.event_store import EventStore
C:L6:class HealthEngineV2[L7:__init__,L11:calculate_score,L25:get_status,L37:get_detailed_health]
F:L7:def __init__()->[]; L11:def calculate_score()->['int', 'm.get', 'max', 'min']; L25:def get_status()->['self.calculate_score']; L37:def get_detailed_health()->['self._event_store.get_stats', 'self._metrics.get_summary', 'self.calculate_score', 'self.get_status']
N:-

## `runtime\observability\resource_monitor.py`
I:L1:import psutil; L2:import threading; L3:import time; L4:from typing import Dict; L4:from typing import Optional
C:L6:class ResourceMonitor[L7:__init__,L14:start,L22:stop,L28:_monitor_loop,L34:_collect_resources]
F:L7:def __init__()->['threading.Event']; L14:def start()->['self._stop_event.clear', 'self._thread.start', 'threading.Thread']; L22:def stop()->['self._stop_event.set', 'self._thread.join']; L28:def _monitor_loop()->['self._collect_resources', 'self._stop_event.wait']; L34:def _collect_resources()->['proc.cpu_percent', 'proc.memory_info', 'proc.num_threads', 'proc.oneshot']
N:-

# 18. Configuration

## `bot\config.py`
I:L1:from __future__ import annotations; L3:import os; L4:from dataclasses import dataclass; L30:import json
C:L8:class BotConfig[]
F:L15:def get_bot_config()->['BotConfig', 'RuntimeError', 'cfg.get', "cfg.get('bot_token', '').strip"]; L52:def get_hub_url()->['os.environ.get', 'render_url.strip', 'url.strip']
N:L29:open

## `runtime\plugin_config_manager.py`
I:L1:import json; L2:import os; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Optional; L4:from pathlib import Path
C:L6:class PluginConfigManager[L7:__init__,L13:load_all_configs,L23:get_config,L27:update_config,L45:create_default_config,L55:validate_config]
F:L7:def __init__()->['Path', 'self.config_dir.mkdir', 'self.load_all_configs']; L13:def load_all_configs()->['json.load', 'open', 'print', 'self.config_dir.glob']; L23:def get_config()->['self.configs.get']; L27:def update_config()->['json.dump', 'json.dumps', 'open', 'print']; L45:def create_default_config()->['self.update_config']; L55:def validate_config()->['isinstance']
N:L18:open; L35:open

# 19. Logging

## `plugins\logger_plugin.py`
I:L2:from plugins.plugin_base import PluginBase
C:L4:class LoggerPlugin(PluginBase)[L17:on_init,L20:on_load,L24:on_enable,L27:on_disable,L30:on_error,L33:on_unload,L36:on_event]
F:L17:def on_init()->['print']; L20:def on_load()->['print', 'self.PLUGIN_INFO.get', 'self.load_config']; L24:def on_enable()->['print']; L27:def on_disable()->['print']; L30:def on_error()->['print']; L33:def on_unload()->['print']; L36:def on_event()->['len', 'print', 'self.config.get']
N:-

## `runtime\funpay_catalog.py`
I:L17:from __future__ import annotations; L18:import os; L18:import re; L18:import json; L18:import time; L19:from typing import List; L19:from typing import Dict; L19:from typing import Optional; L21:from runtime.http_client import HTTPClient; L21:from runtime.http_client import HTTPClientError
C:-
F:L34:def _ensure_dir()->['os.makedirs']; L58:def fetch_all_subcategories()->['RE_GAME_BLOCK.findall', 'RE_GAME_TITLE.search', 'RE_SUB_LINK.finditer', '_ensure_dir']; L142:def get_cached()->['json.load', 'open', 'os.path.exists']
N:L71:open; L134:open; L146:open

## `runtime\runtime_log.py`
I:L2:import time; L3:from typing import List; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Optional; L4:from enum import Enum; L5:from collections import deque
C:L8:class LogLevel(Enum)[]; L15:class RuntimeLogEntry[L16:__init__,L23:to_dict,L32:__str__]; L36:class RuntimeLog[L39:__init__,L43:add,L48:info,L51:warning,L54:error,L57:debug,L60:get_entries,L68:get_all]
F:L16:def __init__()->['time.strftime', 'time.time']; L23:def to_dict()->[]; L32:def __str__()->[]; L39:def __init__()->['deque']; L43:def add()->['RuntimeLogEntry', 'self._entries.append']; L48:def info()->['self.add']; L51:def warning()->['self.add']; L54:def error()->['self.add']; L57:def debug()->['self.add']; L60:def get_entries()->['e.to_dict', 'list'] (+5 more)
N:-

## `web\logs_api.py`
I:L1:from flask import Blueprint; L1:from flask import jsonify; L1:from flask import request; L1:from flask import current_app; L1:from flask import Response; L2:import sys; L2:import os; L2:import json; L2:import time; L4:from runtime.runtime_log import RuntimeLog; L4:from runtime.runtime_log import LogLevel
C:-
F:L10:def _get_runtime_log()->['getattr']; L17:def _get_observability()->['getattr']; L21:def _seed_demo_logs()->['rl.count', 'rl.debug', 'rl.error', 'rl.info']; L33:def list_logs()->['LogLevel', '_get_runtime_log', '_seed_demo_logs', "e['message'].lower"]; L56:def logs_stats()->['_get_runtime_log', '_seed_demo_logs', 'by_level.get', 'e.get']; L70:def clear_logs()->['_get_runtime_log', 'jsonify', 'logs_bp.route', 'rl.clear']; L77:def export_logs()->["'\\n'.join", 'Response', '_get_runtime_log', 'e.get']; L92:def add_test_log()->['LogLevel', '_get_runtime_log', 'body.get', "body.get('level', 'INFO').upper"]; L107:def list_events()->['_get_observability', 'int', 'jsonify', 'len']
N:-

## `runtime\notifications\channels\log_channel.py`
I:L2:from runtime.notifications.channels.base_channel import BaseChannel; L3:from runtime.notifications.notification_types import Notification
C:L5:class LogChannel(BaseChannel)[L6:__init__,L9:send]
F:L6:def __init__()->[]; L9:def send()->['notification.type.value.upper', 'self.runtime_log.error', 'self.runtime_log.info']
N:-

# 20. Backup

## `runtime\backup_manager.py`
I:L9:import os; L10:import time; L11:import shutil; L12:import threading; L13:import logging; L14:from pathlib import Path; L15:from datetime import datetime; L16:from typing import Optional
C:L21:class BackupManager[L22:__init__,L35:start,L39:stop,L46:backup_now,L72:restore,L98:list_backups,L109:_start_daily_backup]
F:L22:def __init__()->['Path', 'Path(__file__).resolve', 'self._backup_dir.mkdir', 'threading.Event']; L35:def start()->['logger.info', 'self._start_daily_backup']; L39:def stop()->['self._stop.set', 'self._worker.is_alive', 'self._worker.join']; L46:def backup_now()->['datetime.now', 'datetime.now().strftime', 'logger.error', 'logger.info']; L72:def restore()->['Path', 'logger.error', 'logger.info', 'self._db_path.exists']; L98:def list_backups()->['self._backup_dir.exists', 'self._backup_dir.iterdir', 'sorted', 'str']; L109:def _start_daily_backup()->['datetime.now', 'datetime.now().strftime', 'logger.error', 'self._stop.is_set']; L110:def _loop()->['datetime.now', 'datetime.now().strftime', 'logger.error', 'self._stop.is_set']
N:-

## `runtime\backup\backup_manager.py`
I:L2:import os; L3:import json; L4:import zipfile; L5:import hashlib; L6:import shutil; L7:from datetime import datetime; L8:from typing import Dict; L8:from typing import Any; L8:from typing import Optional; L9:from runtime.backup.models import BackupMetadata; L9:from runtime.backup.models import BackupInfo
C:L12:class BackupManager[L13:__init__,L18:_get_state_manager,L27:_get_plugin_manager,L30:_get_observability_hub,L35:_get_recovery_manager,L40:_get_boot_journal,L45:create_backup,L120:_create_snapshot]
F:L13:def __init__()->['os.makedirs']; L18:def _get_state_manager()->['hasattr']; L27:def _get_plugin_manager()->[]; L30:def _get_observability_hub()->['hasattr']; L35:def _get_recovery_manager()->['hasattr']; L40:def _get_boot_journal()->['getattr', 'hasattr']; L45:def create_backup()->['BackupInfo', 'BackupMetadata', 'boot_journal.load', 'datetime.utcnow']; L120:def _create_snapshot()->['datetime.utcnow', 'datetime.utcnow().timestamp', 'obs.get_detailed_health', 'obs.get_plugin_metrics']; L139:def _get_dir_size()->['os.path.getsize', 'os.path.join', 'os.walk']; L147:def _compute_checksum()->['f.read', 'hashlib.sha256', 'open', 'os.path.join'] (+3 more)
N:L60:open; L66:open; L71:open; L79:open; L85:open; L92:open; L105:open; L153:open

## `runtime\backup\models.py`
I:L2:from dataclasses import dataclass; L2:from dataclasses import field; L3:from typing import Dict; L3:from typing import Any; L3:from typing import Optional; L3:from typing import List; L4:from datetime import datetime
C:L8:class BackupMetadata[]; L18:class BackupInfo[]
F:-
N:-

## `runtime\backup\restore_manager.py`
I:L2:import os; L3:import json; L4:import zipfile; L5:import shutil; L6:import tempfile; L7:from typing import Dict; L7:from typing import Any; L8:from runtime.backup.models import BackupInfo
C:L11:class RestoreManager[L12:__init__,L25:restore_from_backup]
F:L12:def __init__()->['getattr', 'hasattr']; L25:def restore_from_backup()->['json.load', 'open', 'os.path.exists', 'os.path.join']
N:L39:open; L53:open; L60:open; L69:open

## `runtime\backup\scheduler.py`
I:L2:import threading; L3:import time; L4:from typing import Optional; L5:from runtime.backup.backup_manager import BackupManager
C:L8:class BackupScheduler[L9:__init__,L17:start,L26:stop,L33:_loop,L39:_create_backup_and_rotate,L48:_rotate_backups]
F:L9:def __init__()->['threading.Event']; L17:def start()->['print', 'self._stop_event.clear', 'self._thread.start', 'threading.Thread']; L26:def stop()->['print', 'self._stop_event.set', 'self._thread.join']; L33:def _loop()->['self._create_backup_and_rotate', 'self._stop_event.wait']; L39:def _create_backup_and_rotate()->['print', 'self._rotate_backups', 'self.backup_manager.create_backup']; L48:def _rotate_backups()->['len', 'print', 'self.backup_manager.delete_backup', 'self.backup_manager.list_backups']
N:-

## `runtime\backup\__init__.py`
I:L2:from runtime.backup.models import BackupMetadata; L2:from runtime.backup.models import BackupInfo; L3:from runtime.backup.backup_manager import BackupManager; L4:from runtime.backup.restore_manager import RestoreManager; L5:from runtime.backup.scheduler import BackupScheduler
C:-
F:-
N:-

## `runtime\migrations\backup_migrations.py`
C:-
F:-
N:-

# 21. Open questions / gaps

- Manual review required for runtime integration details not visible in static analysis.
- Dynamic imports, decorators, and metaclasses may hide additional dependencies.
- Network/IO pattern matching is heuristic; review flagged lines for completeness.
