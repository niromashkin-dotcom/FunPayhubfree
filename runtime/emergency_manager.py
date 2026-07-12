"""
Emergency Manager — система состояний для FunPayHub.

Состояния:
  NORMAL    → всё работает штатно
  WARNING   → обнаружена проблема (баланс 0, ошибки API)
  PAUSED    → частичная остановка (один поставщик)
  EMERGENCY → полная остановка (критическая проблема)

Триггеры перехода:
  - Баланс поставщика 0                     → WARNING / PAUSED
  - N ошибок API подряд                     → WARNING
  - Рост отмен заказов > порог              → WARNING
  - Задержка ответа поставщика > X минут    → PAUSED
  - Множественные сбои                     → EMERGENCY
"""

import time
import logging
import threading
from typing import Optional, Set

logger = logging.getLogger("FunPayHUB.Emergency")


class EmergencyManager:
    """Управляет состоянием системы и аварийными остановками."""

    # ── Состояния ──────────────────────────────────────────────────
    NORMAL    = "NORMAL"
    WARNING   = "WARNING"
    PAUSED    = "PAUSED"
    EMERGENCY = "EMERGENCY"

    def __init__(self, event_bus, seller_service=None, plugin_manager=None,
                 admin_chat_id: str = ""):
        self._eb = event_bus
        self._svc = seller_service
        self._pm = plugin_manager
        self._admin_chat_id = admin_chat_id

        self._state = self.NORMAL
        self._state_since = time.time()
        self._lock = threading.RLock()

        # Счётчики ошибок по поставщикам
        self._error_counts: dict = {}
        self._supplier_warnings: Set[str] = set()
        self._paused_suppliers: Set[str] = set()

        # Пороги
        self.WARN_AFTER_ERRORS = 3        # WARNING после 3 ошибок подряд
        self.PAUSE_AFTER_MINUTES = 10     # PAUSED если поставщик молчит >10 мин
        self.EMERGENCY_CANCEL_RATE = 0.3  # EMERGENCY если 30% заказов отменены

        # Telegram bot settings
        self._tg_bot_url = ""
        tg_url = getattr(event_bus, '_telegram_bot_url', '') if event_bus else ''

    # ── Публичный API ──────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_normal(self) -> bool:
        return self._state == self.NORMAL

    @property
    def is_emergency(self) -> bool:
        return self._state == self.EMERGENCY

    def start(self):
        """Запустить мониторинг."""
        logger.info(f"[Emergency] Manager started. State: {self._state}")

    def stop(self):
        logger.info("[Emergency] Manager stopped")

    # ── Проверки (вызываются из health-check или воркера) ──────────

    def check_supplier(self, supplier: str, is_online: bool):
        """Проверить состояние поставщика и обновить состояние системы."""
        with self._lock:
            if not is_online:
                self._error_counts[supplier] = self._error_counts.get(supplier, 0) + 1
            else:
                self._error_counts[supplier] = 0
                self._supplier_warnings.discard(supplier)
                self._paused_suppliers.discard(supplier)

            err_count = self._error_counts.get(supplier, 0)

            # WARNING: N ошибок подряд
            if err_count >= self.WARN_AFTER_ERRORS and self._state == self.NORMAL:
                if supplier not in self._supplier_warnings:
                    self._supplier_warnings.add(supplier)
                    msg = (f"⚠️ WARNING: {supplier} — {err_count} ошибок подряд.\n"
                           f"Перевожу в WARNING")
                    self._set_state(self.WARNING, msg)
                return

            # PAUSED: поставщик недоступен > порога
            if err_count >= self.WARN_AFTER_ERRORS + 2 and supplier not in self._paused_suppliers:
                self._paused_suppliers.add(supplier)
                self._deactivate_supplier(supplier)
                msg = (f"⏸️ PAUSED: {supplier} — {err_count} ошибок.\n"
                       f"Лоты поставщика сняты с продажи.")
                self._set_state(self.PAUSED, msg)

    def check_cancel_rate(self, total_orders: int, cancelled_orders: int):
        """Проверить долю отмен — при превышении EMERGENCY."""
        if total_orders < 5:
            return  # слишком мало заказов для статистики
        rate = cancelled_orders / max(total_orders, 1)
        if rate >= self.EMERGENCY_CANCEL_RATE and self._state != self.EMERGENCY:
            msg = (f"🚨 EMERGENCY: {rate:.0%} заказов отменено "
                   f"({cancelled_orders}/{total_orders}).\n"
                   f"Аварийная остановка!")
            self.emergency_stop(msg)

    # ── Действия ─────────────────────────────────────────────────

    def emergency_stop(self, reason: str = ""):
        """Полная аварийная остановка (EMERGENCY)."""
        with self._lock:
            self._set_state(self.EMERGENCY, reason)
            self._deactivate_all_lots()
            self._notify_admin(
                f"🚨🚨🚨 EMERGENCY STOP 🚨🚨🚨\n"
                f"Причина: {reason or 'Неизвестна'}\n"
                f"Все лоты сняты. Новые заказы не принимаются.\n"
                f"Текущие заказы будут доделаны."
            )

    def resume(self):
        """Вернуть систему в NORMAL."""
        with self._lock:
            self._error_counts.clear()
            self._supplier_warnings.clear()
            self._paused_suppliers.clear()
            self._set_state(self.NORMAL, "Система возвращена в штатный режим")
            self._activate_all_lots()

    # ── Внутренние методы ──────────────────────────────────────────

    def _set_state(self, new_state: str, reason: str = ""):
        old = self._state
        if old == new_state:
            return
        self._state = new_state
        self._state_since = time.time()
        logger.warning(f"[Emergency] {old} → {new_state}: {reason}")
        self._notify_admin(f"🔄 Состояние: {old} → {new_state}\n{reason}")

        # Публикуем событие
        if self._eb:
            try:
                self._eb.publish("emergency_state_change", {
                    "old_state": old,
                    "new_state": new_state,
                    "reason": reason,
                    "timestamp": time.time(),
                })
            except Exception:
                pass

    def _deactivate_supplier(self, supplier: str):
        """Снять лоты одного поставщика."""
        try:
            from runtime.http_client import HTTPClient
            from bot.config import get_hub_url
            hc = HTTPClient()
            hc.post(f"{get_hub_url()}/api/seller/lots/deactivate",
                     json={"supplier": supplier}, timeout=10)
            logger.info(f"[Emergency] Lots deactivated for {supplier}")
        except Exception:
            pass

    def _deactivate_all_lots(self):
        """Снять ВСЕ лоты."""
        try:
            from runtime.http_client import HTTPClient
            from bot.config import get_hub_url
            hc = HTTPClient()
            hc.post(f"{get_hub_url()}/api/seller/lots/deactivate",
                     json={"all": True}, timeout=10)
            logger.info("[Emergency] All lots deactivated")
        except Exception:
            pass

    def _activate_all_lots(self):
        """Восстановить все лоты."""
        try:
            from runtime.http_client import HTTPClient
            from bot.config import get_hub_url
            hc = HTTPClient()
            hc.post(f"{get_hub_url()}/api/seller/lots/activate",
                     json={"all": True}, timeout=10)
            logger.info("[Emergency] All lots reactivated")
        except Exception:
            pass

    def _notify_admin(self, text: str):
        """Отправить уведомление админу в Telegram."""
        if not text or not self._admin_chat_id:
            return
        try:
            from runtime.http_client import HTTPClient
            hc = HTTPClient()
            hc.post(
                f"https://api.telegram.org/bot"
                f"{self._get_bot_token()}/sendMessage",
                json={"chat_id": self._admin_chat_id, "text": text,
                       "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception:
            pass

    def _get_bot_token(self) -> str:
        """Получить токен бота из окружения."""
        import os
        return os.environ.get("TELEGRAM_BOT_TOKEN", "")

    # ── Состояние для API ─────────────────────────────────────────

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "state": self._state,
                "since": self._state_since,
                "age_seconds": time.time() - self._state_since,
                "error_counts": dict(self._error_counts),
                "paused_suppliers": list(self._paused_suppliers),
                "warnings": list(self._supplier_warnings),
            }
