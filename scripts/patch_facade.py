import sys
import re

file_path = r"d:\Projects\FunPayHub\runtime\seller_service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

prop_code = """
    @property
    def order_service(self):
        if not hasattr(self, '_order_svc'):
            from runtime.services.order_service import OrderService
            from runtime.services.delivery_service import DeliveryService
            from runtime.services.finance_service import FinanceService
            from runtime.services.chat_service import ChatService
            class FallbackMM:
                def send_message(self, c, t): pass
                def get_chat_history(self, c): return []
            cs = ChatService(FallbackMM())
            ds = DeliveryService(self.event_bus, cs)
            fs = FinanceService(self.event_bus)
            self._order_svc = OrderService(self.event_bus, ds, fs, cs)
        return self._order_svc

    def _emit_event(self, event_type: str, payload: dict):
"""
content = content.replace('    def _emit_event(self, event_type: str, payload: dict):', prop_code)

old_refund = """    def refund_order(self, order_id, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "order_id": order_id, "message": "Проверка пройдена"}
                acc.refund(order_id)
                self._cache.pop("orders", None)
                return {"ok": True, "dry_run": False, "order_id": order_id, "message": "Возврат оформлен"}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}"""

new_refund = """    def refund_order(self, order_id, dry_run: bool = True) -> dict:
        with self._lock:
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "order_id": order_id, "message": "Проверка пройдена"}
                
                # FACADE: delegating to OrderService
                self.order_service.refund_order(order_id)
                self._cache.pop("orders", None)
                
                return {"ok": True, "dry_run": False, "order_id": order_id, "message": "Возврат оформлен через OrderService"}
            except Exception as e:
                return {"ok": False, "error": str(e)}"""

if old_refund in content:
    content = content.replace(old_refund, new_refund)
else:
    print("Failed to find refund_order block")
    sys.exit(1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully")
