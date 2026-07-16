import re

file_path = r"d:\Projects\FunPayHub\runtime\seller_service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

prop_code = """
    @property
    def lot_service(self):
        if not hasattr(self, '_lot_svc'):
            from runtime.services.lot_service import LotService
            self._lot_svc = LotService(self._get_account)
        return self._lot_svc

    @property
    def order_service(self):
"""
if "def lot_service(self):" not in content:
    content = content.replace('    @property\n    def order_service(self):', prop_code)

stubs = {
    "get_my_lots": "    def get_my_lots(self, force_refresh=False) -> dict:\n        with self._lock:\n            return self.lot_service.get_my_lots(force_refresh)\n",
    "get_lot_details": "    def get_lot_details(self, lot_id: int) -> dict:\n        with self._lock:\n            return self.lot_service.get_lot_details(lot_id)\n",
    "update_lot_price": "    def update_lot_price(self, lot_id: int, new_price: float, dry_run: bool = True) -> dict:\n        with self._lock:\n            return self.lot_service.update_lot_price(lot_id, new_price, dry_run)\n",
    "toggle_lot_active": "    def toggle_lot_active(self, lot_id: int, active: bool, dry_run: bool = True) -> dict:\n        with self._lock:\n            return self.lot_service.toggle_lot_active(lot_id, active, dry_run)\n",
    "bulk_update_prices": "    def bulk_update_prices(self, changes: list, dry_run: bool = True) -> dict:\n        with self._lock:\n            return self.lot_service.bulk_update_prices(changes, dry_run)\n",
    "raise_category_lots": "    def raise_category_lots(self, category_id: int, dry_run: bool = True) -> dict:\n        with self._lock:\n            return self.lot_service.raise_category_lots(category_id, dry_run)\n",
    "create_lot": "    def create_lot(self, lot_data: dict) -> dict:\n        with self._lock:\n            return self.lot_service.create_lot(lot_data)\n"
}

for method, stub in stubs.items():
    pattern = r"    def " + method + r"\(self.*?(?=\n    def |\n\s*seller_service_singleton)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        old_block = match.group(0)
        content = content.replace(old_block, stub)
        print(f"Patched {method}")
    else:
        print(f"Error finding {method}")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("All proxies set.")
