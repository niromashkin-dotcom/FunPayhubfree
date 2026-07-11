"""
Report Engine — ежедневные и по запросу отчёты (Этап D).

- Ежедневный отчёт в 6:00 (МСК): заказы, оборот, прибыль
- Сводка в 21:00: прогноз + прибыльные ниши
- Кнопки по запросу: отчёт, балансы, логи
"""

import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger("FunPayHUB.Reports")

# Московское время (UTC+3)
MSK = timezone(timedelta(hours=3))


class ReportEngine:
    """Генерация и отправка отчётов."""

    def __init__(self, event_bus=None, admin_chat_id: str = ""):
        self._eb = event_bus
        self._admin_chat_id = admin_chat_id
        self._worker = None
        self._stop = threading.Event()

    def start(self):
        """Запустить планировщик отчётов."""
        self._start_scheduler()
        logger.info("[Reports] Engine started")

    def stop(self):
        self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    # ── Планировщик ────────────────────────────────────────────────

    def _start_scheduler(self):
        def _loop():
            while not self._stop.is_set():
                try:
                    now = datetime.now(MSK)
                    # Отчёт в 6:00
                    if now.hour == 6 and now.minute == 0:
                        self.send_daily_report()
                        time.sleep(61)  # не сработать дважды
                    # Сводка в 21:00
                    elif now.hour == 21 and now.minute == 0:
                        self.send_evening_summary()
                        time.sleep(61)
                except Exception as e:
                    logger.error(f"[Reports] Scheduler error: {e}")
                time.sleep(30)
        self._worker = threading.Thread(target=_loop, name="Reports", daemon=True)
        self._worker.start()

    # ── Отчёты ─────────────────────────────────────────────────────

    def send_daily_report(self):
        """Ежедневный отчёт за прошедшие сутки (6:00 → 6:00)."""
        now = time.time()
        day_start = now - 86400  # 24 часа назад

        text = self._build_daily_report(day_start, now)
        self._send_admin(text)
        logger.info("[Reports] Daily report sent")

    def send_evening_summary(self):
        """Вечерняя сводка в 21:00."""
        now = time.time()
        day_start = now - 86400

        report = self._build_daily_report(day_start, now)
        forecast = self._build_forecast()

        text = (
            f"📊 ВЕЧЕРНЯЯ СВОДКА (21:00)\n\n"
            f"{report}\n\n"
            f"🔮 Прогноз:\n{forecast}"
        )
        self._send_admin(text)
        logger.info("[Reports] Evening summary sent")

    def send_report_on_demand(self) -> str:
        """Отчёт по запросу (кнопка в Telegram)."""
        now = time.time()
        day_start = now - (now % 86400)  # с начала текущих суток
        return self._build_daily_report(day_start, now)

    # ── Построение отчёта ──────────────────────────────────────────

    def _build_daily_report(self, since: float, until: float) -> str:
        """Сформировать текст отчёта за период."""
        try:
            from runtime.database.ledger import Ledger
            report = Ledger.get_daily_report(since, until)
        except Exception:
            return "📊 Отчёт временно недоступен (БД)"

        income = report.get("total_income", 0)
        expenses = report.get("total_expenses", 0)
        profit = report.get("total_profit", 0)
        orders = report.get("order_count", 0)
        by_type = report.get("by_type", {})

        lines = [
            f"📊 ОТЧЁТ ЗА ПЕРИОД",
            f"━━━━━━━━━━━━━━━━━",
            f"📦 Заказов: {orders}",
            f"💰 Доход: {income:.2f} ₽",
            f"💸 Расходы: {abs(expenses):.2f} ₽",
            f"📈 Прибыль: {profit:.2f} ₽",
            f"━━━━━━━━━━━━━━━━━",
        ]

        # Детализация по типам
        for tx_type, amount in sorted(by_type.items()):
            if amount != 0:
                emoji = {"funpay_income": "🟢", "provider_payment": "🔴",
                         "commission": "⚪", "refund": "🔵", "profit": "💎"}.get(tx_type, "•")
                lines.append(f"{emoji} {tx_type}: {amount:.2f} ₽")

        return "\n".join(lines)

    def _build_forecast(self) -> str:
        """Прогноз + бизнес-метрики (Этап L)."""
        try:
            from runtime.database.repository import Repository
            from runtime.database.ledger import Ledger
            from runtime.database.base import get_session
            from runtime.database.models import Order, Provider
            from sqlalchemy import func

            now = time.time()
            week_ago = now - 7 * 86400
            month_ago = now - 30 * 86400

            report = Ledger.get_daily_report(week_ago, now)
            weekly_profit = report.get("total_profit", 0)
            daily_avg = weekly_profit / 7 if weekly_profit else 0

            # ── Данные из БД ──
            session = get_session()
            try:
                # Заказы по дням недели
                total_orders = session.query(func.count(Order.id)).filter(
                    Order.started_at >= month_ago).scalar() or 0

                # Эффективность поставщиков
                providers_data = []
                providers = session.query(Provider).all()
                for p in providers:
                    p_orders = session.query(func.count(Order.id)).filter(
                        Order.provider_id == p.id,
                        Order.started_at >= week_ago).scalar() or 0
                    if p_orders > 0:
                        providers_data.append(f"  • {p.name}: {p_orders} заказов/нед")
            finally:
                session.close()

            lines = [
                f"  • Средняя прибыль/день: {daily_avg:.2f} ₽",
                f"  • Прогноз на неделю: {daily_avg * 7:.2f} ₽",
                f"  • Прогноз на месяц: {daily_avg * 30:.2f} ₽",
                f"  • Заказов за 30 дней: {total_orders}",
            ]
            if providers_data:
                lines.append("  ─── Поставщики ───")
                lines.extend(providers_data)

            return "\n".join(lines)
        except Exception:
            return "Прогноз временно недоступен"

    # ── Отправка ──────────────────────────────────────────────────

    def _get_main_menu_markup(self):
        """Return inline keyboard JSON matching tg_bot_service.main_menu()."""
        # Buttons as defined in tg_bot_service.py after our edits
        keyboard = [
            [
                {"text": "🚀 Старт системы", "callback_data": "start_hub"},
                {"text": "🛑 Стоп системы", "callback_data": "stop_hub"}
            ],
            [
                {"text": "📊 Отчёт сейчас", "callback_data": "report"},
                {"text": "📜 Логи", "callback_data": "logs_view"}
            ],
            [
                {"text": "💰 Баланс", "callback_data": "balance"},
                {"text": "🔥 Симуляция", "callback_data": "simulation"}
            ],
            [
                {"text": "⚠️ Состояние системы", "callback_data": "system_status"},
                {"text": "📦 Лоты", "callback_data": "create_lots"}
            ],
            [
                {"text": "🤖 AI агент", "callback_data": "ai_agent"},
                {"text": "💳 Кошелёк", "callback_data": "wallet"}
            ]
        ]
        return {"inline_keyboard": keyboard}

    def _send_admin(self, text: str, reply_markup=None):
        if not text or not self._admin_chat_id:
            return
        try:
            from runtime.http_client import HTTPClient
            import os, json
            hc = HTTPClient()
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            if token:
                payload = {
                    "chat_id": self._admin_chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup or json.dumps(self._get_main_menu_markup())
                }
                hc.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json=payload,
                    timeout=10,
                )
        except Exception as e:
            logger.error(f"[Reports] Send failed: {e}")
