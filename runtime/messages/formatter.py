from __future__ import annotations

import re
from typing import Any, Dict, Optional
from .templates import MessageTemplate, get_template


class MessageFormatter:
    MAX_LENGTH = 4096

    def __init__(self, db_provider: Any = None, api_provider: Any = None) -> None:
        self._db = db_provider
        self._api = api_provider

    def format(self, category: str, key: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        template = get_template(category, key)
        if not template:
            return None
        ctx = dict(context) if context else {}
        self._enrich_context(category, key, ctx)
        try:
            text = template.text.format(**ctx)
        except KeyError as exc:
            missing = str(exc)
            text = template.text.replace("{" + missing + "}", f"[{missing}]")
        text = self._clean(text)
        if len(text) > self.MAX_LENGTH:
            text = text[: self.MAX_LENGTH - 3] + "..."
        return text

    def _enrich_context(self, category: str, key: str, ctx: Dict[str, Any]) -> None:
        if "order_title" not in ctx:
            order = self._load_order_from_db(ctx.get("order_id", ""))
            if order:
                ctx["order_title"] = self.build_order_title(order)
                if "price" not in ctx:
                    try:
                        ctx["price"] = f"{float(order.get('price', 0)):.0f}"
                    except Exception:
                        ctx["price"] = "0"
                if "buyer" not in ctx:
                    ctx["buyer"] = order.get("buyer_name") or order.get("buyer") or "Покупатель"
                if "link" not in ctx and order.get("link"):
                    ctx["link"] = order["link"]
                if "eta" not in ctx:
                    ctx["eta"] = self._resolve_eta_from_order(order)

        if "eta" not in ctx:
            ctx["eta"] = self.build_eta_text(None)

    def _load_order_from_db(self, order_id: str) -> Optional[Dict[str, Any]]:
        try:
            if not self._db or not order_id:
                return None
            return self._db.get_order(order_id)
        except Exception:
            return None

    def _resolve_eta_from_order(self, order: Dict[str, Any]) -> str:
        service_tag = order.get("service_tag", "")
        tag = (service_tag or "").lower()
        if "premium" in tag or "tg" in tag:
            return "10"
        if "boost" in tag or "discord" in tag:
            return "5"
        if "stars" in tag:
            return "15"
        return "4"

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.strip()

    def build_order_title(self, order: Dict[str, Any]) -> str:
        title = order.get("title") or order.get("order_title") or "Заказ"
        title = re.sub(r"\[.*?\]", "", title).strip()
        return title or "Заказ"

    def build_eta_text(self, eta_minutes: Optional[int]) -> str:
        if eta_minutes is None:
            return "2–6"
        if eta_minutes <= 1:
            return "1–2"
        if eta_minutes >= 60:
            hours = eta_minutes // 60
            minutes = eta_minutes % 60
            parts = []
            if hours:
                parts.append(f"{hours} ч.")
            if minutes:
                parts.append(f"{minutes} мин.")
            return " ".join(parts) if parts else str(eta_minutes)
        return str(eta_minutes)

    def build_delivery_data(self, delivery: Dict[str, Any]) -> Dict[str, str]:
        return {
            "login": str(delivery.get("login", "")),
            "email": str(delivery.get("email", "")),
            "password": str(delivery.get("password", "")),
        }
