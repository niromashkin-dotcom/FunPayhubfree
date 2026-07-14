from __future__ import annotations

import threading
import time
import logging
from typing import Any, Dict, Optional, Set
from .formatter import MessageFormatter
from .templates import get_template

logger = logging.getLogger("FunPayHUB.Messages.Manager")


class MessageManager:
    """Единый центр управления всеми исходящими сообщениями покупателю.

    Никакой другой код не должен отправлять сообщения напрямую.
    Все пути: MessageManager → Sender.send_chat_message / admin channel.
    """

    def __init__(
        self,
        sender: Any = None,
        db_provider: Any = None,
        api_provider: Any = None,
        admin_chat_id: str = "",
    ) -> None:
        self._sender = sender
        self._formatter = MessageFormatter(db_provider=db_provider, api_provider=api_provider)
        self._sent: Set[str] = set()
        self._lock = threading.Lock()
        self._order_stages: Dict[str, int] = {}
        self._admin_chat_id = admin_chat_id
        self._db = db_provider
        self._api = api_provider

    def set_sender(self, sender: Any) -> None:
        self._sender = sender

    def set_admin_chat_id(self, chat_id: str) -> None:
        self._admin_chat_id = chat_id

    def _now(self) -> float:
        return time.time()

    def _mark_sent(self, order_id: str, stage: str) -> None:
        with self._lock:
            key = f"{order_id}:{stage}"
            self._sent.add(key)

    def _is_sent(self, order_id: str, stage: str) -> bool:
        with self._lock:
            return f"{order_id}:{stage}" in self._sent

    def send(
        self,
        order_id: str,
        chat_id: str,
        category: str,
        key: str,
        context: Optional[Dict[str, Any]] = None,
        force: bool = False,
        record: bool = True,
    ) -> bool:
        dedup_key = f"{order_id}:{category}.{key}"
        if not force and self._is_sent(order_id, dedup_key):
            return False
        text = self._formatter.format(category, key, context)
        if not text:
            return False
        if not self._sender:
            logger.warning(f"[MessageManager] No sender configured, cannot send {category}.{key}")
            return False
        try:
            result = self._sender.send_chat_message(chat_id, text, dry_run=False)
            ok = result.get("ok", False) if isinstance(result, dict) else bool(result)
            if ok:
                self._mark_sent(order_id, dedup_key)
                if record and self._db:
                    try:
                        self._db.log_notification(
                            order_id=int(order_id) if str(order_id).isdigit() else None,
                            chat_id=str(chat_id),
                            category=category,
                            key=key,
                            text=text,
                            context=context,
                            delivery_status="sent",
                        )
                    except Exception:
                        pass
                logger.info(f"[MessageManager] Sent {category}.{key} order={order_id} chat={chat_id}")
            else:
                err = result.get("error", "") if isinstance(result, dict) else ""
                logger.warning(f"[MessageManager] Send failed {category}.{key}: {err}")
                if record and self._db:
                    try:
                        self._db.log_notification(
                            order_id=int(order_id) if str(order_id).isdigit() else None,
                            chat_id=str(chat_id),
                            category=category,
                            key=key,
                            text=text,
                            context=context,
                            delivery_status="failed",
                            error=err,
                        )
                    except Exception:
                        pass
            return ok
        except Exception as exc:
            logger.error(f"[MessageManager] Send exception {category}.{key}: {exc}")
            return False

    def send_admin(
        self,
        category: str,
        key: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        text = self._formatter.format(category, key, context)
        if not text or not self._admin_chat_id:
            return False
        try:
            import requests
            from bot.config import get_hub_url, get_secret
            token = get_secret("TELEGRAM_NOTIFIER_BOT_TOKEN", "") or ""
            if token:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": self._admin_chat_id, "text": text, "parse_mode": "HTML"},
                    timeout=10,
                )
                logger.info(f"[MessageManager] Admin sent {category}.{key}")
                return True
        except Exception as exc:
            logger.error(f"[MessageManager] Admin send failed {category}.{key}: {exc}")
        return False

    def get_order_stage(self, order_id: str) -> int:
        return self._order_stages.get(order_id, 0)

    def set_order_stage(self, order_id: str, stage: int) -> None:
        self._order_stages[order_id] = stage

    def clear_sent(self, order_id: str, category_key: Optional[str] = None) -> None:
        with self._lock:
            if category_key:
                self._sent.discard(f"{order_id}:{category_key}")
            else:
                to_remove = [k for k in self._sent if k.startswith(f"{order_id}:")]
                for k in to_remove:
                    self._sent.discard(k)

    def mark_sent(self, order_id: str, category_key: str) -> None:
        self._mark_sent(order_id, category_key)

    @property
    def formatter(self) -> MessageFormatter:
        return self._formatter
