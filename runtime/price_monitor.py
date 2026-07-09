"""
Price Monitor - автоматическая коррекция цен
"""
import time
from pathlib import Path

def auto_adjust_prices(svc, dry_run=True):
    my_lots = svc.get_my_lots()
    if not my_lots.get("available"):
        return {"ok": False, "error": "Не удалось загрузить лоты"}
    suggestions = []
    for lot in my_lots.get("lots", []):
        lot_id = lot.get("id")
        sub_id = lot.get("subcategory_id")
        sub_type = lot.get("subcategory_type", 0)
        my_price = lot.get("price")
        if not sub_id:
            continue
        scan = svc.scan_market(sub_id, sub_type, force_refresh=False)
        if not scan.get("available"):
            continue
        other_lots = [l for l in scan.get("lots", []) if not l.get("is_mine")]
        other_prices = sorted([l["price"] for l in other_lots if l.get("price")])
        if len(other_prices) < 3:
            continue
        cheaper_count = sum(1 for p in other_prices if p < my_price)
        if cheaper_count >= 3:
            avg_cheaper = sum(p for p in other_prices if p < my_price) / cheaper_count
            if my_price > avg_cheaper * 1.1:
                suggestions.append({
                    "lot_id": lot_id,
                    "title": lot.get("title"),
                    "current_price": my_price,
                    "suggested_price": round(avg_cheaper, 2),
                    "reason": f"{cheaper_count} конкурентов дешевле"
                })
                if not dry_run:
                    svc.update_lot_price(lot_id, round(avg_cheaper, 2), dry_run=False)
    return {"ok": True, "suggestions": suggestions, "count": len(suggestions)}