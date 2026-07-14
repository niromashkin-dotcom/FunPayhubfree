import time
import threading

def _safe_error(e):
    return str(e)

class LotService:
    def __init__(self, account_provider):
        self.get_account = account_provider
        self._cache = {}
        self._cache_time = {}
        self._lock = threading.RLock()

    def _cached(self, key: str, ttl: int = 60):
        if key in self._cache:
            if time.time() - self._cache_time.get(key, 0) < ttl:
                return self._cache[key]
            else:
                self._cache.pop(key, None)
                self._cache_time.pop(key, None)
        return None

    def _set_cache(self, key: str, data, ttl: int = 0):
        self._cache[key] = data
        self._cache_time[key] = time.time()

    def get_my_lots(self, force_refresh=False) -> dict:
        with self._lock:
            if not force_refresh:
                cached = self._cached("my_lots", ttl=120)
                if cached:
                    return cached
            acc = self.get_account()
            if acc is None:
                return {"available": False, "error": "Нет авторизации", "lots": [], "categories": [], "total": 0}
            try:
                user = acc.get_user(acc.id)
                raw_lots = user.get_lots() if hasattr(user, "get_lots") else []
                lots = []
                categories = {}
                for lot in raw_lots:
                    lot_id = getattr(lot, "id", None)
                    title = getattr(lot, "title", "") or getattr(lot, "description", "") or "(без названия)"
                    price = getattr(lot, "price", None)
                    amount = getattr(lot, "amount", None)
                    server = getattr(lot, "server", None)
                    subcat = getattr(lot, "subcategory", None)
                    cat_name = "Прочее"
                    subcat_name = ""
                    if subcat is not None:
                        subcat_name = getattr(subcat, "name", "") or ""
                        parent = getattr(subcat, "category", None)
                        if parent is not None:
                            cat_name = getattr(parent, "name", "Прочее") or "Прочее"
                    subcat_id_val = None
                    subcat_type_val = 0
                    if subcat is not None:
                        subcat_id_val = getattr(subcat, "id", None)
                        subcat_type_obj = getattr(subcat, "type", None)
                        if subcat_type_obj is not None:
                            subcat_type_val = getattr(subcat_type_obj, "value", 0)
                    item = {
                        "id": lot_id,
                        "title": str(title)[:300],
                        "price": price,
                        "amount": amount,
                        "server": str(server) if server else None,
                        "category_name": cat_name,
                        "subcategory_name": subcat_name,
                        "subcategory_id": subcat_id_val,
                        "subcategory_type": subcat_type_val,
                        "url": "https://funpay.com/lots/offer?id=" + str(lot_id) if lot_id else None,
                    }
                    lots.append(item)
                    if cat_name not in categories:
                        categories[cat_name] = {"name": cat_name, "count": 0}
                    categories[cat_name]["count"] += 1
                result = {
                    "available": True,
                    "total": len(lots),
                    "lots": lots,
                    "categories": list(categories.values()),
                    "updated_at": time.time()
                }
                self._set_cache("my_lots", result)
                return result
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "lots": [], "categories": [], "total": 0}

    def get_lot_details(self, lot_id: int) -> dict:
        with self._lock:
            cache_key = "lot_" + str(lot_id)
            cached = self._cached(cache_key, ttl=120)
            if cached:
                return cached
            acc = self.get_account()
            if acc is None:
                return {"available": False, "error": "Нет авторизации"}
            try:
                base = None
                my_lots_cache = self._cache.get("my_lots")
                if my_lots_cache:
                    for l in my_lots_cache.get("lots", []):
                        if l.get("id") == lot_id:
                            base = dict(l)
                            break
                if base is None:
                    user = acc.get_user(acc.id)
                    raw_lots = user.get_lots() if hasattr(user, "get_lots") else []
                    for lot in raw_lots:
                        if getattr(lot, "id", None) == lot_id:
                            base = {
                                "id": lot.id,
                                "title": str(getattr(lot, "title", "") or "")[:300],
                                "description": str(getattr(lot, "description", "") or "")[:2000],
                                "price": getattr(lot, "price", None),
                                "amount": getattr(lot, "amount", None),
                                "server": str(getattr(lot, "server", "")) if getattr(lot, "server", None) else None,
                            }
                            sub = getattr(lot, "subcategory", None)
                            if sub is not None:
                                base["subcategory_name"] = getattr(sub, "name", "") or ""
                                par = getattr(sub, "category", None)
                                base["category_name"] = getattr(par, "name", "") if par else ""
                            break
                if base is None:
                    return {"available": False, "error": "Лот не найден"}
                extra = {}
                try:
                    fields = acc.get_lot_fields(lot_id)
                    extra["active"] = getattr(fields, "active", None)
                    extra["deactivate_after_sale"] = getattr(fields, "deactivate_after_sale", None)
                    extra["renew"] = getattr(fields, "renew", None)
                    raw_fields = getattr(fields, "fields", None)
                    if isinstance(raw_fields, dict):
                        clean = {}
                        for k, v in raw_fields.items():
                            try:
                                clean[str(k)] = str(v)[:500] if v is not None else None
                            except Exception:
                                pass
                        extra["raw_fields"] = clean
                except Exception as fe:
                    extra["fields_error"] = _safe_error(fe)
                base["extra"] = extra
                base["url"] = "https://funpay.com/lots/offer?id=" + str(lot_id)
                base["updated_at"] = time.time()
                base["available"] = True
                self._set_cache(cache_key, base)
                return base
            except Exception as e:
                return {"available": False, "error": _safe_error(e)}

    def update_lot_price(self, lot_id: int, new_price: float, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self.get_account()
            if acc is None:
                return {"ok": False, "error": "Нет авторизации"}
            try:
                fields = acc.get_lot_fields(lot_id)
                old_price = getattr(fields, "price", None)
                if dry_run:
                    return {"ok": True, "dry_run": True, "lot_id": lot_id, "old_price": old_price, "new_price": new_price}
                fields.price = new_price
                acc.save_lot(fields)
                self._cache.pop("my_lots", None)
                self._cache.pop("lot_" + str(lot_id), None)
                return {"ok": True, "dry_run": False, "lot_id": lot_id, "old_price": old_price, "new_price": new_price}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def toggle_lot_active(self, lot_id: int, active: bool, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self.get_account()
            if acc is None:
                return {"ok": False, "error": "Нет авторизации"}
            try:
                fields = acc.get_lot_fields(lot_id)
                old_active = getattr(fields, "active", None)
                if dry_run:
                    return {"ok": True, "dry_run": True, "lot_id": lot_id, "old_active": old_active, "new_active": active}
                fields.active = active
                acc.save_lot(fields)
                self._cache.pop("my_lots", None)
                self._cache.pop("lot_" + str(lot_id), None)
                return {"ok": True, "dry_run": False, "lot_id": lot_id, "old_active": old_active, "new_active": active}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def bulk_update_prices(self, changes: list, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self.get_account()
            if acc is None:
                return {"ok": False, "error": "Нет авторизации", "results": []}
            results = []
            success_count = 0
            fail_count = 0
            for ch in changes:
                lot_id = ch.get("lot_id")
                new_price = ch.get("new_price")
                if not lot_id or new_price is None:
                    results.append({"lot_id": lot_id, "ok": False, "error": "Неверные параметры"})
                    fail_count += 1
                    continue
                try:
                    fields = acc.get_lot_fields(int(lot_id))
                    old_price = getattr(fields, "price", None)
                    if not dry_run:
                        fields.price = float(new_price)
                        acc.save_lot(fields)
                        self._cache.pop("lot_" + str(lot_id), None)
                    results.append({"lot_id": lot_id, "ok": True, "old_price": old_price, "new_price": float(new_price)})
                    success_count += 1
                except Exception as e:
                    results.append({"lot_id": lot_id, "ok": False, "error": _safe_error(e)})
                    fail_count += 1
            if not dry_run:
                self._cache.pop("my_lots", None)
            return {"ok": True, "dry_run": dry_run, "success": success_count, "failed": fail_count, "results": results}

    def raise_category_lots(self, category_id: int, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self.get_account()
            if acc is None:
                return {"ok": False, "error": "Нет авторизации"}
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "category_id": category_id}
                acc.raise_lots(category_id)
                self._cache.pop("my_lots", None)
                return {"ok": True, "dry_run": False, "category_id": category_id}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}

    def create_lot(self, lot_data: dict) -> dict:
        with self._lock:
            acc = self.get_account()
            if acc is None:
                return {"ok": False, "error": "Нет авторизации"}
            try:
                title = str(lot_data.get("title", ""))
                descr = str(lot_data.get("description", ""))
                price = float(lot_data.get("price") or 0)
                amount = int(lot_data.get("amount") or 1)
                if not title or not price:
                    return {"ok": False, "error": "Название и цена обязательны"}
                from FunPayAPI import types as _fp_types
                fields = {
                    "fields[summary][ru]": title,
                    "fields[summary][en]": title,
                    "fields[desc][ru]": descr,
                    "fields[desc][en]": descr,
                    "price": str(price),
                    "amount": str(amount),
                    "active": "on",
                }
                subcat = None
                node_id = 0
                try:
                    subcat_id = int(lot_data.get("subcategory_id") or 0)
                    if subcat_id:
                        for cat in acc.get_sorted_categories().values():
                            subcat = cat.get_subcategory(_fp_types.SubCategoryTypes.COMMON, subcat_id)
                            if subcat:
                                break
                    if subcat is None and lot_data.get("category_id"):
                        category = acc.get_category(int(lot_data["category_id"]))
                        if category:
                            subs = [s for s in category.get_subcategories() if getattr(s, "type", None) is _fp_types.SubCategoryTypes.COMMON]
                            if subs:
                                subcat = subs[0]
                    if subcat is not None:
                        node_id = subcat.id
                        fields["node_id"] = str(node_id)
                except Exception:
                    pass
                lot_fields = _fp_types.LotFields(0, fields, subcategory=subcat)
                acc.save_lot(lot_fields)
                self._cache.pop("my_lots", None)
                return {"ok": True}
            except Exception as e:
                import traceback
                return {"ok": False, "error": traceback.format_exc()}
