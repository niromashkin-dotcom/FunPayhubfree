from flask import Blueprint, jsonify, request
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runtime.seller_service import seller_service_singleton as svc
try:
    from runtime.lot_generator import LotGenerator
except Exception:
    LotGenerator = None

seller_bp = Blueprint("seller", __name__)


@seller_bp.route("/api/version")
def version():
    return jsonify({"version": "2.0.0"})


@seller_bp.route("/api/seller/status")
def status():
    return jsonify({"has_credentials": svc.has_credentials()})


@seller_bp.route("/api/seller/credentials", methods=["POST"])
def set_credentials():
    body = request.json or {}
    golden_key = body.get("golden_key", "").strip()
    user_agent = body.get("user_agent", "").strip()
    if not golden_key:
        return jsonify({"error": "golden_key обязателен"}), 400
    ok = svc.save_credentials(golden_key, user_agent or None)
    if not ok:
        return jsonify({"error": "Не удалось сохранить"}), 500
    test = svc.test_connection()
    return jsonify({"saved": True, "test": test})


@seller_bp.route("/api/seller/credentials", methods=["DELETE"])
def delete_credentials():
    return jsonify({"cleared": svc.clear_credentials()})


@seller_bp.route("/api/seller/overview")
def overview():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.get_account_overview(force_refresh=force))


@seller_bp.route("/api/seller/balance")
def balance():
    lot_id = int(request.args.get("lot_id", 0))
    return jsonify(svc.get_balance(lot_id=lot_id))


@seller_bp.route("/api/seller/balance/full")
def balance_full():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.get_balance_full(force_refresh=force))


@seller_bp.route("/api/seller/balance/history")
def balance_history():
    limit = int(request.args.get("limit", 200))
    return jsonify(svc.get_balance_history(limit=limit))


@seller_bp.route("/api/seller/balance/history", methods=["DELETE"])
def clear_balance_history():
    return jsonify(svc.clear_balance_history())


@seller_bp.route("/api/seller/wallets")
def wallets():
    return jsonify(svc.get_wallets() if hasattr(svc, "get_wallets") else {"wallets": []})


@seller_bp.route("/api/seller/test", methods=["POST"])
def test_conn():
    return jsonify(svc.test_connection())


@seller_bp.route("/api/seller/lots")
def my_lots():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.get_my_lots(force_refresh=force))


@seller_bp.route("/api/seller/lots/<int:lot_id>")
def lot_details(lot_id):
    return jsonify(svc.get_lot_details(lot_id))


@seller_bp.route("/api/seller/lots/<int:lot_id>/price", methods=["POST"])
def update_price(lot_id):
    body = request.json or {}
    try:
        new_price = float(body.get("new_price"))
    except Exception:
        return jsonify({"ok": False, "error": "Неверная цена"}), 400
    dry_run = bool(body.get("dry_run", True))
    return jsonify(svc.update_lot_price(lot_id, new_price, dry_run=dry_run))


@seller_bp.route("/api/seller/lots/<int:lot_id>/active", methods=["POST"])
def toggle_active(lot_id):
    body = request.json or {}
    active = bool(body.get("active", True))
    dry_run = bool(body.get("dry_run", True))
    return jsonify(svc.toggle_lot_active(lot_id, active, dry_run=dry_run))


@seller_bp.route("/api/seller/lots/bulk-price", methods=["POST"])
def bulk_price():
    body = request.json or {}
    changes = body.get("changes") or []
    dry_run = bool(body.get("dry_run", True))
    if not isinstance(changes, list) or not changes:
        return jsonify({"ok": False, "error": "Список изменений пуст"}), 400
    return jsonify(svc.bulk_update_prices(changes, dry_run=dry_run))


@seller_bp.route("/api/seller/categories/<int:category_id>/raise", methods=["POST"])
def raise_cat(category_id):
    body = request.json or {}
    dry_run = bool(body.get("dry_run", True))
    return jsonify(svc.raise_category_lots(category_id, dry_run=dry_run))


@seller_bp.route("/api/seller/sales")
def sales():
    force = request.args.get("force", "false").lower() == "true"
    include_closed = request.args.get("closed", "true").lower() == "true"
    include_refunded = request.args.get("refunded", "true").lower() == "true"
    return jsonify(svc.get_sales_data(force_refresh=force, include_closed=include_closed, include_refunded=include_refunded))


@seller_bp.route("/api/seller/orders")
def orders():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.get_orders_data(force_refresh=force))


@seller_bp.route("/api/seller/chats/<chat_id>/messages")
def chat_messages(chat_id):
    limit = int(request.args.get("limit", 50))
    return jsonify(svc.get_chat_messages(chat_id, limit=limit))


@seller_bp.route("/api/seller/chats/<chat_id>/send", methods=["POST"])
def send_message(chat_id):
    body = request.json or {}
    text = body.get("text", "")
    dry_run = bool(body.get("dry_run", True))
    return jsonify(svc.send_chat_message(chat_id, text, dry_run=dry_run))


@seller_bp.route("/api/seller/orders/<order_id>/refund", methods=["POST"])
def refund(order_id):
    body = request.json or {}
    dry_run = bool(body.get("dry_run", True))
    return jsonify(svc.refund_order(order_id, dry_run=dry_run))


@seller_bp.route("/api/seller/customers")
def customers():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.get_customers_data(force_refresh=force))


@seller_bp.route("/api/seller/customers/<buyer_id>")
def customer_details(buyer_id):
    return jsonify(svc.get_customer_details(buyer_id))


@seller_bp.route("/api/seller/notifications")
def account_notifications():
    only_unack = request.args.get("only_unack", "false").lower() == "true"
    limit = int(request.args.get("limit", 200))
    type_filter = request.args.get("type") or None
    return jsonify(svc.get_account_notifications(only_unack=only_unack, limit=limit, type_filter=type_filter))


@seller_bp.route("/api/seller/notifications/collect", methods=["POST"])
def collect_notifications():
    return jsonify(svc.collect_account_notifications())


@seller_bp.route("/api/seller/notifications/<notif_id>/ack", methods=["POST"])
def ack_notification(notif_id):
    return jsonify(svc.ack_account_notification(notif_id))


@seller_bp.route("/api/seller/notifications/<notif_id>/dismiss", methods=["POST"])
def dismiss_notification(notif_id):
    return jsonify(svc.dismiss_account_notification(notif_id))


@seller_bp.route("/api/seller/notifications", methods=["DELETE"])
def clear_notifications():
    return jsonify(svc.clear_account_notifications())


@seller_bp.route("/api/market/categories")
def market_categories():
    return jsonify(svc.get_my_categories())


@seller_bp.route("/api/market/scan")
def market_scan():
    subcategory_id = int(request.args.get("subcategory_id", 0))
    subcategory_type = int(request.args.get("subcategory_type", 0))
    force = request.args.get("force", "false").lower() == "true"
    if not subcategory_id:
        return jsonify({"available": False, "error": "subcategory_id обязателен"}), 400
    return jsonify(svc.scan_market(subcategory_id, subcategory_type, force_refresh=force))


@seller_bp.route("/api/market/compare")
def compare_prices():
    from flask import request
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.compare_my_prices(force_refresh=force))


@seller_bp.route("/api/market/optimal/<int:lot_id>")
def calculate_optimal(lot_id):
    strategy = request.args.get("strategy", "competitive")
    params = {}
    if request.args.get("position"):
        params["position"] = request.args.get("position")
    if request.args.get("cost"):
        params["cost"] = request.args.get("cost")
    if request.args.get("margin_pct"):
        params["margin_pct"] = request.args.get("margin_pct")
    return jsonify(svc.calculate_optimal_price(lot_id, strategy=strategy, params=params))


@seller_bp.route("/api/market/simulate/<int:lot_id>")
def simulate_price(lot_id):
    try:
        new_price = float(request.args.get("new_price", 0))
    except Exception:
        return jsonify({"ok": False, "error": "Неверная цена"}), 400
    return jsonify(svc.simulate_price(lot_id, new_price))


@seller_bp.route("/api/market/optimize-all", methods=["POST"])
def optimize_all():
    body = request.json or {}
    strategy = body.get("strategy", "competitive")
    dry_run = bool(body.get("dry_run", True))
    return jsonify(svc.optimize_all_lots(strategy=strategy, dry_run=dry_run))


@seller_bp.route("/api/market/competitors")
def list_competitors():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.get_competitors(force_refresh=force))


@seller_bp.route("/api/market/competitors/<seller_id>")
def competitor_details(seller_id):
    return jsonify(svc.get_competitor_details(seller_id))


@seller_bp.route("/api/market/competitors/<seller_id>/track", methods=["POST"])
def track_competitor(seller_id):
    body = request.json or {}
    name = body.get("name", "")
    return jsonify(svc.track_competitor(seller_id, name))


@seller_bp.route("/api/market/competitors/<seller_id>/track", methods=["DELETE"])
def untrack_competitor(seller_id):
    return jsonify(svc.untrack_competitor(seller_id))


@seller_bp.route("/api/market/watchlist")
def get_watchlist():
    return jsonify(svc.get_watchlist())


@seller_bp.route("/api/market/heatmap", methods=["GET", "POST"])
def heatmap():
    mode = request.args.get("mode", "quick")
    if request.method == "POST":
        mode = "full"
    return jsonify(svc.analyze_heatmap(mode=mode))


@seller_bp.route("/api/market/niches")
def list_niches():
    source = request.args.get("source", "all")
    return jsonify(svc.find_niches(source=source))


@seller_bp.route("/api/market/niches/<int:subcategory_id>/compare")
def compare_niche(subcategory_id):
    return jsonify(svc.compare_niche_with_mine(subcategory_id))


@seller_bp.route("/api/suppliers")
def list_suppliers():
    category = request.args.get("category")
    status = request.args.get("status")
    return jsonify(svc.get_suppliers(category_filter=category, status_filter=status))


@seller_bp.route("/api/suppliers/<supplier_id>")
def get_supplier(supplier_id):
    return jsonify(svc.get_supplier_by_id(supplier_id))


@seller_bp.route("/api/suppliers", methods=["POST"])
def add_supplier():
    body = request.json or {}
    return jsonify(svc.add_supplier(body))


@seller_bp.route("/api/suppliers/<supplier_id>", methods=["DELETE"])
def delete_supplier(supplier_id):
    return jsonify(svc.delete_supplier(supplier_id))


@seller_bp.route("/api/lots/<int:lot_id>/supplier", methods=["POST"])
def link_lot_supplier(lot_id):
    body = request.json or {}
    sid = body.get("supplier_id")
    cost = body.get("cost", 0)
    if not sid:
        return jsonify({"ok": False, "error": "supplier_id обязателен"}), 400
    return jsonify(svc.link_lot_to_supplier(lot_id, sid, cost))


@seller_bp.route("/api/lots/<int:lot_id>/supplier", methods=["DELETE"])
def unlink_lot_supplier(lot_id):
    return jsonify(svc.unlink_lot(lot_id))


@seller_bp.route("/api/lot-suppliers")
def lot_suppliers():
    return jsonify(svc.get_lot_suppliers())


@seller_bp.route("/api/margin/overview")
def margin_overview():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.get_margin_overview(force_refresh=force))


@seller_bp.route("/api/margin/calc")
def margin_calc():
    try:
        price = float(request.args.get("price", 0))
        cost = float(request.args.get("cost", 0))
    except Exception:
        return jsonify({"ok": False, "error": "Неверные значения"}), 400
    commission = request.args.get("commission")
    commission_val = float(commission) if commission else None
    return jsonify(svc.calculate_margin(price, cost, commission_pct=commission_val))


@seller_bp.route("/api/margin/settings")
def margin_settings():
    return jsonify(svc.get_margin_settings())


@seller_bp.route("/api/margin/settings", methods=["POST"])
def save_margin_settings():
    body = request.json or {}
    try:
        pct = float(body.get("commission_pct", 10))
    except Exception:
        return jsonify({"ok": False, "error": "Неверное значение"}), 400
    return jsonify(svc.save_margin_settings(pct))


@seller_bp.route("/api/market/ratings")
def seller_ratings():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.analyze_seller_ratings(force_refresh=force))


@seller_bp.route("/api/market/ratings/<seller_id>")
def seller_rating_details(seller_id):
    return jsonify(svc.get_seller_details(seller_id))


@seller_bp.route("/api/market/alerts")
def list_market_alerts():
    type_filter = request.args.get("type") or None
    only_unack = request.args.get("only_unack", "false").lower() == "true"
    limit = int(request.args.get("limit", 200))
    return jsonify(svc.get_market_alerts(type_filter=type_filter, only_unack=only_unack, limit=limit))


@seller_bp.route("/api/market/alerts/collect", methods=["POST"])
def collect_market_alerts_endpoint():
    return jsonify(svc.collect_market_alerts())


@seller_bp.route("/api/market/alerts/<alert_id>/ack", methods=["POST"])
def ack_market_alert(alert_id):
    return jsonify(svc.ack_market_alert(alert_id))


@seller_bp.route("/api/market/alerts/<alert_id>/dismiss", methods=["POST"])
def dismiss_market_alert(alert_id):
    return jsonify(svc.dismiss_market_alert(alert_id))


@seller_bp.route("/api/market/alerts", methods=["DELETE"])
def clear_market_alerts():
    return jsonify(svc.clear_market_alerts())


@seller_bp.route("/api/market/alerts/settings")
def get_alert_settings():
    return jsonify(svc.get_alert_settings())


@seller_bp.route("/api/market/alerts/settings", methods=["POST"])
def save_alert_settings():
    body = request.json or {}
    return jsonify(svc.save_alert_settings(body))


@seller_bp.route("/api/autoreply/templates")
def list_templates():
    return jsonify(svc.get_templates())


@seller_bp.route("/api/autoreply/templates", methods=["POST"])
def add_template():
    body = request.json or {}
    if not body.get('name') or not body.get('text'):
        return jsonify({'ok': False, 'error': 'name и text обязательны'}), 400
    return jsonify(svc.add_template(body))


@seller_bp.route("/api/autoreply/templates/<template_id>", methods=["DELETE"])
def delete_template(template_id):
    return jsonify(svc.delete_template(template_id))


@seller_bp.route("/api/autoreply/templates/<template_id>/preview")
def preview_template(template_id):
    return jsonify(svc.preview_template(template_id))


@seller_bp.route("/api/autoreply/rules")
def list_rules():
    return jsonify(svc.get_autoreply_rules())


@seller_bp.route("/api/autoreply/rules", methods=["POST"])
def save_rule():
    body = request.json or {}
    if not body.get('name') or not body.get('trigger') or not body.get('template_id'):
        return jsonify({'ok': False, 'error': 'name, trigger, template_id обязательны'}), 400
    return jsonify(svc.save_autoreply_rule(body))


@seller_bp.route("/api/autoreply/rules/<rule_id>", methods=["DELETE"])
def delete_rule(rule_id):
    return jsonify(svc.delete_autoreply_rule(rule_id))


@seller_bp.route("/api/autoreply/rules/<rule_id>/toggle", methods=["POST"])
def toggle_rule(rule_id):
    # Tolerant body parsing: accept JSON, form, query params, or empty (toggle).
    body = {}
    try:
        body = request.get_json(silent=True, force=True) or {}
    except Exception:
        body = {}
    if not body and request.form:
        body = request.form.to_dict()
    if not body and request.args:
        body = request.args.to_dict()
    if "enabled" in body:
        enabled = str(body.get("enabled")).lower() in ("1", "true", "yes", "on")
    else:
        try:
            rules = svc.get_autoreply_rules() or {}
            rlist = rules.get("rules", rules) if isinstance(rules, dict) else rules
            current = False
            if isinstance(rlist, list):
                for r in rlist:
                    if str(r.get("id")) == str(rule_id):
                        current = bool(r.get("enabled", False))
                        break
            enabled = not current
        except Exception:
            enabled = True
    return jsonify(svc.toggle_autoreply_rule(rule_id, enabled))

@seller_bp.route("/api/autoreply/test", methods=["POST"])
def autoreply_test():
    body = request.json or {}
    chat_id = body.get('chat_id')
    template_id = body.get('template_id')
    dry_run = bool(body.get('dry_run', True))
    if not chat_id or not template_id:
        return jsonify({'ok': False, 'error': 'chat_id и template_id обязательны'}), 400
    return jsonify(svc.send_autoreply_test(chat_id, template_id, ctx=body.get('ctx'), dry_run=dry_run))


@seller_bp.route("/api/autoreply/log")
def autoreply_log():
    limit = int(request.args.get('limit', 100))
    return jsonify(svc.get_autoreply_log(limit=limit))


@seller_bp.route("/api/autoreply/log", methods=["DELETE"])
def clear_autoreply_log():
    return jsonify(svc.clear_autoreply_log())


@seller_bp.route("/api/autodelivery/settings")
def autodelivery_settings_get():
    return jsonify(svc.get_autodelivery_settings())


@seller_bp.route("/api/autodelivery/settings", methods=["POST"])
def autodelivery_settings_save():
    body = request.json or {}
    return jsonify(svc.save_autodelivery_settings(body))


@seller_bp.route("/api/autodelivery/bindings")
def autodelivery_bindings():
    return jsonify(svc.get_autodelivery_bindings())


@seller_bp.route("/api/autodelivery/bindings", methods=["POST"])
def autodelivery_save_binding():
    body = request.json or {}
    return jsonify(svc.save_binding(body))


@seller_bp.route("/api/autodelivery/bindings/<binding_id>", methods=["DELETE"])
def autodelivery_delete_binding(binding_id):
    return jsonify(svc.delete_binding(binding_id))


@seller_bp.route("/api/autodelivery/stock/<lot_id>")
def autodelivery_stock_get(lot_id):
    return jsonify(svc.get_stock(lot_id))


@seller_bp.route("/api/autodelivery/stock/<lot_id>", methods=["POST"])
def autodelivery_stock_add(lot_id):
    body = request.json or {}
    items = body.get('items', [])
    mode = body.get('mode', 'append')
    return jsonify(svc.add_stock_items(lot_id, items, mode=mode))


@seller_bp.route("/api/autodelivery/stock/<lot_id>/<int:index>", methods=["DELETE"])
def autodelivery_stock_remove(lot_id, index):
    return jsonify(svc.remove_stock_item(lot_id, index))


@seller_bp.route("/api/autodelivery/stock/<lot_id>", methods=["DELETE"])
def autodelivery_stock_clear(lot_id):
    return jsonify(svc.clear_stock(lot_id))


@seller_bp.route("/api/autodelivery/log")
def autodelivery_log_get():
    limit = int(request.args.get('limit', 100))
    return jsonify(svc.get_delivery_log(limit=limit))


@seller_bp.route("/api/autodelivery/log", methods=["DELETE"])
def autodelivery_log_clear():
    return jsonify(svc.clear_delivery_log())


@seller_bp.route("/api/autodelivery/process", methods=["POST"])
def autodelivery_process():
    body = request.json or {}
    dry_run = body.get('dry_run')
    return jsonify(svc.process_autodelivery_once(dry_run=dry_run))


@seller_bp.route("/api/automation/tasks")
def automation_tasks():
    return jsonify(svc.get_automation_tasks())


@seller_bp.route("/api/automation/tasks", methods=["POST"])
def automation_save_task():
    body = request.json or {}
    return jsonify(svc.save_automation_task(body))


@seller_bp.route("/api/automation/tasks/<task_id>/toggle", methods=["POST"])
def automation_toggle(task_id):
    body = request.json or {}
    return jsonify(svc.toggle_automation_task(task_id, body.get('enabled', False)))


@seller_bp.route("/api/automation/tasks/<task_id>/run", methods=["POST"])
def automation_run(task_id):
    body = request.json or {}
    dry = body.get('dry_run')
    return jsonify(svc.run_automation_task(task_id, force_dry_run=dry))


@seller_bp.route("/api/automation/log")
def automation_log():
    limit = int(request.args.get('limit', 100))
    return jsonify(svc.get_automation_log(limit=limit))


@seller_bp.route("/api/automation/log", methods=["DELETE"])
def automation_log_clear():
    return jsonify(svc.clear_automation_log())


@seller_bp.route("/api/automation/reset", methods=["POST"])
def automation_reset():
    return jsonify(svc.reset_automation_tasks())


@seller_bp.route("/api/system/backups")
def list_backups_endpoint():
    backup_type = request.args.get('type')
    return jsonify(svc.list_backups(backup_type=backup_type))


@seller_bp.route("/api/system/backups", methods=["POST"])
def create_backup_endpoint():
    body = request.json or {}
    label = body.get('label', '')
    backup_type = body.get('type', 'full')
    return jsonify(svc.create_backup(label=label, backup_type=backup_type))


@seller_bp.route("/api/system/backups/<name>/restore", methods=["POST"])
def restore_backup_endpoint(name):
    body = request.json or {}
    dry_run = bool(body.get('dry_run', True))
    return jsonify(svc.restore_backup(name, dry_run=dry_run))


@seller_bp.route("/api/system/backups/<name>", methods=["DELETE"])
def delete_backup_endpoint(name):
    return jsonify(svc.delete_backup(name))


@seller_bp.route("/api/system/backups/<name>/download")
def download_backup(name):
    from flask import send_file
    path = svc.get_backup_file_path(name)
    if path:
        return send_file(path, as_attachment=True, download_name=name)
    return jsonify({'error': 'Не найдено'}), 404


@seller_bp.route("/api/system/health")
def system_health():
    return jsonify(svc.check_system_health())


@seller_bp.route("/api/ai/recommendations")
def ai_advisor():
    force = request.args.get("force", "false").lower() == "true"
    return jsonify(svc.generate_ai_recommendations(force_refresh=force))


# B17: badges endpoint
@seller_bp.route("/api/seller/badges")
def get_badges_b17():
    try:
        data = svc.get_account_notifications(only_unack=True, limit=500)
        notifs = data.get("notifications", []) if isinstance(data, dict) else []
        if not isinstance(notifs, list):
            notifs = []
        counts = {"notifications": 0, "orders": 0, "customers": 0, "alerts": 0}
        for n in notifs:
            if not isinstance(n, dict):
                continue
            counts["notifications"] += 1
            t = n.get("type", "")
            if t == "new_order":
                counts["orders"] += 1
            elif t == "chat_message":
                counts["customers"] += 1
            elif t in ("system_alert", "plugin_alert", "market_alert", "new_review"):
                counts["alerts"] += 1
        return jsonify({"ok": True, "counts": counts})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "counts": {}})


@seller_bp.route("/api/seller/badges/mark_read", methods=["POST"])
def mark_badges_read_b17():
    try:
        body = request.get_json(silent=True) or {}
        section = body.get("section", "")
        type_map = {
            "notifications": None,
            "orders": ["new_order"],
            "customers": ["chat_message"],
            "alerts": ["system_alert", "plugin_alert", "market_alert", "new_review"],
        }
        types = type_map.get(section)
        data = svc.get_account_notifications(only_unack=True, limit=500)
        notifs = data.get("notifications", []) if isinstance(data, dict) else []
        marked = 0
        for n in notifs:
            if not isinstance(n, dict):
                continue
            if types is not None and n.get("type") not in types:
                continue
            nid = n.get("id")
            if nid:
                try:
                    svc.acknowledge_notification(nid)
                    marked += 1
                except Exception:
                    pass
        return jsonify({"ok": True, "marked": marked, "section": section})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# B30: simulator endpoints — для теста AutoSMM/AutoReply без реальных заказов
@seller_bp.route("/api/dev/simulate/new_order", methods=["POST"])
def sim_new_order_b30():
    """Симулирует событие new_order — AutoSMM/AutoReply среагируют как на настоящее.
    Body: { "chat_id": "users-X-Y", "lot_title": "...[AS#4961]", "order_id": "TEST123", "buyer_username": "test_buyer", "price": 40 }
    """
    try:
        body = request.get_json(silent=True) or {}
        chat_id = body.get("chat_id") or "users-19952092-20188266"
        lot_title = body.get("lot_title") or "Тестовый лот [AS#4961]"
        order_id = body.get("order_id") or ("SIM" + str(int(__import__("time").time()))[-6:])
        buyer = body.get("buyer_username") or "test_buyer"
        buyer_id = body.get("buyer_id") or 19952092
        price = body.get("price") or 40
        lot_id = body.get("lot_id") or 71357594
        
        event = {
            "type": "new_order",
            "order_id": order_id,
            "lot_id": lot_id,
            "chat_id": chat_id,
            "buyer": buyer,
            "buyer_id": buyer_id,
            "buyer_username": buyer,
            "price": price,
            "title": lot_title,
            "lot_title": lot_title,
            "url": "https://funpay.com/orders/" + order_id + "/",
            "_simulated": True,
        }
        
        # Используем event_bus из seller_service
        bus = getattr(svc, "event_bus", None)
        if bus is None:
            return jsonify({"ok": False, "error": "event_bus not connected to seller_service"})
        
        bus.emit("new_order", event)
        print("[B30-SIM] emitted new_order: " + str(order_id) + " title=" + lot_title[:50])
        
        return jsonify({"ok": True, "emitted": event, "note": "Check logs — AutoSMM should react"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


@seller_bp.route("/api/dev/simulate/buyer_message", methods=["POST"])
def sim_buyer_message_b30():
    """Симулирует сообщение от покупателя в чате.
    Body: { "chat_id": "users-X-Y", "text": "https://t.me/durov", "from_buyer": true }
    """
    try:
        body = request.get_json(silent=True) or {}
        chat_id = body.get("chat_id") or "users-19952092-20188266"
        text_msg = body.get("text") or ""
        
        event = {
            "type": "new_message",
            "chat_id": chat_id,
            "chat_name": body.get("buyer_username") or "test_buyer",
            "text": text_msg,
            "from_me": False,
            "_simulated": True,
        }
        
        bus = getattr(svc, "event_bus", None)
        if bus is None:
            return jsonify({"ok": False, "error": "event_bus not connected"})
        
        bus.emit("new_message", event)
        print("[B30-SIM] emitted new_message in chat " + str(chat_id) + ": " + text_msg[:80])
        
        return jsonify({"ok": True, "emitted": event})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


@seller_bp.route("/api/dev/simulate/review", methods=["POST"])
def sim_review_b30():
    """Симулирует событие review_received.
    Body: { "stars": 5, "order_id": "TEST123", "chat_id": "users-X-Y", "buyer_id": 19952092, "buyer": "test", "text": "" }
    """
    try:
        body = request.get_json(silent=True) or {}
        stars = int(body.get("stars") or 5)
        order_id = body.get("order_id") or "TEST123"
        chat_id = body.get("chat_id") or "users-19952092-20188266"
        buyer = body.get("buyer") or "test_buyer"
        buyer_id = body.get("buyer_id") or 19952092
        text_review = body.get("text") or ""
        
        event = {
            "type": "review_received",
            "stars": stars,
            "rating": stars,
            "order_id": order_id,
            "chat_id": chat_id,
            "buyer": buyer,
            "buyer_id": buyer_id,
            "text": text_review,
            "detail": "",
            "date_str": "",
            "_simulated": True,
        }
        
        bus = getattr(svc, "event_bus", None)
        if bus is None:
            return jsonify({"ok": False, "error": "event_bus not connected"})
        
        bus.emit("review_received", event)
        print("[B30-SIM] emitted review_received: " + str(stars) + "* on order " + str(order_id))
        
        return jsonify({"ok": True, "emitted": event})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


@seller_bp.route("/api/dev/simulate/full_pipeline", methods=["POST"])
def sim_full_pipeline_b30():
    """Одной кнопкой симулирует ВЕСЬ pipeline:
    1. new_order (с маркером AS#XXX)
    2. Через 3 сек — сообщение покупателя со ссылкой
    3. Через 3 сек — "да" подтверждение
    4. Через 3 сек — отзыв 5 звёзд
    
    Body: { "chat_id": "...", "service_id": "4961", "test_link": "https://t.me/durov" }
    """
    try:
        import threading, time
        body = request.get_json(silent=True) or {}
        chat_id = body.get("chat_id") or "users-19952092-20188266"
        service_id = body.get("service_id") or "4961"
        test_link = body.get("test_link") or "https://t.me/durov"
        delay = float(body.get("delay") or 3)
        
        order_id = "SIM" + str(int(time.time()))[-6:]
        lot_title = "Тестовый лот накрутки [AS#" + str(service_id) + "]"
        
        bus = getattr(svc, "event_bus", None)
        if bus is None:
            return jsonify({"ok": False, "error": "event_bus not connected"})
        
        def _runner():
            # Шаг 1: new_order
            print("[B30-PIPELINE] step 1: new_order")
            bus.emit("new_order", {
                "type": "new_order", "order_id": order_id, "lot_id": 71357594,
                "chat_id": chat_id, "buyer": "test_buyer", "buyer_id": 19952092,
                "buyer_username": "test_buyer", "price": 40,
                "title": lot_title, "lot_title": lot_title,
                "url": "https://funpay.com/orders/" + order_id + "/",
                "_simulated": True,
            })
            time.sleep(delay)
            
            # Шаг 2: ссылка от покупателя
            print("[B30-PIPELINE] step 2: buyer sends link")
            bus.emit("new_message", {
                "type": "new_message", "chat_id": chat_id,
                "chat_name": "test_buyer", "text": test_link,
                "from_me": False, "_simulated": True,
            })
            time.sleep(delay)
            
            # Шаг 3: "да"
            print("[B30-PIPELINE] step 3: buyer confirms 'да'")
            bus.emit("new_message", {
                "type": "new_message", "chat_id": chat_id,
                "chat_name": "test_buyer", "text": "да",
                "from_me": False, "_simulated": True,
            })
            time.sleep(delay * 2)
            
            # Шаг 4: 5 звёзд
            print("[B30-PIPELINE] step 4: 5 stars review")
            bus.emit("review_received", {
                "type": "review_received", "stars": 5, "rating": 5,
                "order_id": order_id, "chat_id": chat_id,
                "buyer": "test_buyer", "buyer_id": 19952092,
                "text": "Все отлично, спасибо!",
                "_simulated": True,
            })
            print("[B30-PIPELINE] done")
        
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        
        return jsonify({"ok": True, "order_id": order_id, "lot_title": lot_title, "note": "Pipeline started — watch logs"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


# B35: sandbox chat — изолированный симулятор для тестов AutoSMM
# Все сообщения хранятся в памяти + JSON файл, не уходят в FunPay
import threading as _b35_th
_b35_lock = _b35_th.Lock()
_b35_messages = []  # [{"from": "buyer"|"seller"|"system", "text": "...", "ts": 1234567890}]
_b35_chat_id = "sandbox-test-chat"

def _b35_load():
    global _b35_messages
    try:
        import json, os
        p = "configs/sandbox_messages.json"
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                _b35_messages = json.load(f) or []
    except Exception:
        _b35_messages = []

def _b35_save():
    try:
        import json
        with open("configs/sandbox_messages.json", "w", encoding="utf-8") as f:
            json.dump(_b35_messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

_b35_load()


@seller_bp.route("/api/dev/sandbox/messages", methods=["GET"])
def b35_get_messages():
    """Список сообщений в sandbox чате."""
    with _b35_lock:
        return jsonify({"ok": True, "messages": list(_b35_messages), "chat_id": _b35_chat_id})


@seller_bp.route("/api/dev/sandbox/clear", methods=["POST"])
def b35_clear():
    """Очистить sandbox чат."""
    global _b35_messages
    with _b35_lock:
        _b35_messages = []
        _b35_save()
    return jsonify({"ok": True, "cleared": True})


@seller_bp.route("/api/dev/sandbox/buyer_send", methods=["POST"])
def b35_buyer_send():
    """Покупатель пишет в sandbox.
    Body: { "text": "..." }
    
    Это создаёт new_message event который AutoSMM обработает."""
    import time as _t
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    if not text:
        return jsonify({"ok": False, "error": "empty text"})
    
    # 1. Добавляем в историю
    with _b35_lock:
        _b35_messages.append({"from": "buyer", "text": text, "ts": _t.time()})
        _b35_save()
    
    # 2. Эмитим как new_message в event_bus (AutoSMM/AutoReply обработают)
    bus = getattr(svc, "event_bus", None)
    if bus:
        bus.emit("new_message", {
            "type": "new_message",
            "chat_id": _b35_chat_id,
            "chat_name": "Sandbox Buyer",
            "text": text,
            "from_me": False,
            "_sandbox": True,
        })
    
    return jsonify({"ok": True, "emitted": True, "text": text})


@seller_bp.route("/api/dev/sandbox/seller_send", methods=["POST"])
def b35_seller_send():
    """Продавец/AutoSMM пишет в sandbox (вызывается перехватчиком).
    Body: { "text": "...", "source": "autosmm"|"autoreply"|"manual" }"""
    import time as _t
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    source = body.get("source", "seller")
    if not text:
        return jsonify({"ok": False, "error": "empty text"})
    
    with _b35_lock:
        _b35_messages.append({"from": "seller", "source": source, "text": text, "ts": _t.time()})
        _b35_save()
    
    return jsonify({"ok": True, "text": text})


@seller_bp.route("/api/dev/sandbox/start_scenario", methods=["POST"])
def b35_start_scenario():
    """Запуск сценария: симуляция нового заказа в sandbox чате.
    Body: { "service_id": "4961", "lot_title": "...", "quantity": 1000 }"""
    import time as _t, uuid as _uuid
    body = request.get_json(silent=True) or {}
    service_id = body.get("service_id") or "4961"
    lot_title = body.get("lot_title") or f"Sandbox Test Lot [AS#{service_id}]"
    order_id = "SAND" + str(int(_t.time()))[-6:]
    
    # 1. Запись в историю
    with _b35_lock:
        _b35_messages.append({
            "from": "system",
            "text": f"🆕 Покупатель ОПЛАТИЛ заказ #{order_id}: {lot_title}",
            "ts": _t.time(),
        })
        _b35_save()
    
    # 2. Эмитим new_order
    bus = getattr(svc, "event_bus", None)
    if bus:
        bus.emit("new_order", {
            "type": "new_order",
            "order_id": order_id,
            "lot_id": 71357594,
            "chat_id": _b35_chat_id,
            "buyer": "sandbox_buyer",
            "buyer_id": 99999,
            "buyer_username": "sandbox_buyer",
            "price": 40,
            "title": lot_title,
            "lot_title": lot_title,
            "url": "https://funpay.com/orders/" + order_id + "/",
            "_sandbox": True,
        })
    
    return jsonify({"ok": True, "order_id": order_id, "lot_title": lot_title})


@seller_bp.route("/api/dev/sandbox/review", methods=["POST"])
def b35_review():
    """Покупатель оставил отзыв в sandbox.
    Body: { "stars": 5 }"""
    import time as _t
    body = request.get_json(silent=True) or {}
    stars = int(body.get("stars") or 5)
    
    with _b35_lock:
        _b35_messages.append({
            "from": "system",
            "text": f"⭐ Покупатель оставил {stars} звёзд",
            "ts": _t.time(),
        })
        _b35_save()
    
    bus = getattr(svc, "event_bus", None)
    if bus:
        bus.emit("review_received", {
            "type": "review_received",
            "stars": stars,
            "rating": stars,
            "order_id": "SAND_LAST",
            "chat_id": _b35_chat_id,
            "buyer": "sandbox_buyer",
            "buyer_id": 99999,
            "text": "",
            "_sandbox": True,
        })
    
    return jsonify({"ok": True, "stars": stars})


# B50: niche scanner — анализ Twiboost услуг для поиска прибыльных ниш
def _b50_load_twiboost_services():
    """Загружает кеш услуг Twiboost."""
    import os, json, sys
    paths = [
        "data/autosmm/twiboost_services_cache.json",
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "data", "autosmm", "twiboost_services_cache.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                services = data.get("services") if isinstance(data, dict) else (data if isinstance(data, list) else [])
                return services or []
            except Exception as e:
                print(f"[B50] load err: {e}")
    return []


def _b50_categorize_service(service):
    """Определяет нишу (platform + type) по названию услуги."""
    import re
    name = (service.get("name") or "").lower()
    cat = (service.get("category") or "").lower()
    full = name + " " + cat
    
    # Платформа
    platform = "other"
    for p in ("telegram", "tg ", "tg-", " tg", "вк ", "vk ", "vkontakte", "instagram", "инстаграм",
              "tiktok", "тикток", "youtube", "ютуб", "twitter", "twitch", "твитч", "kick", "discord",
              "vk.com", "max ", "rutube", "yandex", "яндекс"):
        if p in full:
            platform = p.strip().replace(" ", "").replace("tg", "telegram")
            if "вк" in p or "vk" in p:
                platform = "vk"
            if "twitch" in p or "твитч" in p:
                platform = "twitch"
            if "tiktok" in p or "тикток" in p:
                platform = "tiktok"
            if "youtube" in p or "ютуб" in p:
                platform = "youtube"
            if "instagram" in p or "инстаграм" in p:
                platform = "instagram"
            if "max" in p:
                platform = "max"
            break
    
    # Тип услуги
    stype = "other"
    type_map = [
        ("подписчик", "subscribers"), ("subscriber", "subscribers"), ("follower", "subscribers"),
        ("участник", "subscribers"), ("member", "subscribers"),
        ("просмотр", "views"), ("view", "views"), ("зрител", "viewers"), ("viewer", "viewers"),
        ("лайк", "likes"), ("like", "likes"),
        ("реакц", "reactions"), ("reaction", "reactions"),
        ("коммент", "comments"), ("comment", "comments"),
        ("репост", "shares"), ("share", "shares"),
        ("жалоб", "reports"), ("report", "reports"),
        ("клик", "clicks"), ("click", "clicks"),
        ("premium", "premium"), ("премиум", "premium"),
        ("звезд", "stars"), ("star", "stars"),
        ("бот", "bot"), ("chat", "bot"),
    ]
    for kw, t in type_map:
        if kw in full:
            stype = t
            break
    
    return (platform, stype)


@seller_bp.route("/api/dev/niches/scan", methods=["GET"])
def b50_scan_niches():
    """Сканирует все Twiboost услуги и группирует в ниши.
    Возвращает список ниш с топ-3 самых дешёвых service_id в каждой."""
    services = _b50_load_twiboost_services()
    if not services:
        return jsonify({"ok": False, "error": "Twiboost cache not found", "niches": []})
    
    # Группируем по (platform, type)
    groups = {}
    for s in services:
        platform, stype = _b50_categorize_service(s)
        if platform == "other" or stype == "other":
            continue
        key = (platform, stype)
        if key not in groups:
            groups[key] = []
        try:
            rate = float(s.get("rate", 0))
        except Exception:
            rate = 0
        if rate > 0:
            groups[key].append({
                "service_id": s.get("service_id"),
                "name": s.get("name", ""),
                "rate_per_1000": round(rate, 2),
                "rate_per_1": round(rate / 1000, 4),
                "min": s.get("min", 1),
                "max": s.get("max", 100000),
            })
    
    # Для каждой ниши — топ-3 самых дешёвых
    niches = []
    for (platform, stype), items in groups.items():
        items.sort(key=lambda x: x["rate_per_1000"])
        top3 = items[:3]
        if not top3:
            continue
        cheapest = top3[0]
        # Примерная отпускная цена на FunPay (можно уточнить через парсинг)
        suggested_price_per_1000 = max(cheapest["rate_per_1000"] * 3, cheapest["rate_per_1000"] + 20)
        margin_per_1000 = suggested_price_per_1000 - cheapest["rate_per_1000"]
        margin_percent = round((margin_per_1000 / suggested_price_per_1000) * 100, 1) if suggested_price_per_1000 > 0 else 0
        niches.append({
            "platform": platform,
            "type": stype,
            "label": f"{platform.title()} {stype}",
            "services_count": len(items),
            "cheapest_rate_per_1000": cheapest["rate_per_1000"],
            "suggested_price_per_1000": round(suggested_price_per_1000, 2),
            "margin_percent": margin_percent,
            "top_services": top3,
        })
    
    # Сортируем по марже (max → min)
    niches.sort(key=lambda x: x["margin_percent"], reverse=True)
    
    return jsonify({"ok": True, "total_niches": len(niches), "niches": niches})


@seller_bp.route("/api/dev/niches/budget", methods=["POST"])
def b50_budget_estimate():
    """Расчёт: на сколько заказов хватит бюджета в выбранных нишах.
    Body: { "budget": 100, "niches": ["telegram_subscribers", "tiktok_views"] }"""
    body = request.get_json(silent=True) or {}
    budget = float(body.get("budget") or 0)
    selected = body.get("niches") or []
    
    if budget <= 0 or not selected:
        return jsonify({"ok": False, "error": "budget=0 or no niches selected"})
    
    services = _b50_load_twiboost_services()
    
    # Найдём средний rate среди выбранных ниш
    total_rate = 0
    found = 0
    for s in services:
        platform, stype = _b50_categorize_service(s)
        key = f"{platform}_{stype}"
        if key in selected:
            try:
                rate = float(s.get("rate", 0))
                if rate > 0:
                    total_rate += rate
                    found += 1
            except Exception:
                pass
    
    if found == 0:
        return jsonify({"ok": False, "error": "no services in selected niches"})
    
    avg_rate_per_1000 = total_rate / found
    # Предполагаем что средний заказ — 1000 единиц
    cost_per_order = avg_rate_per_1000
    orders_possible = int(budget / cost_per_order) if cost_per_order > 0 else 0
    
    return jsonify({
        "ok": True,
        "budget": budget,
        "selected_niches": selected,
        "avg_rate_per_1000": round(avg_rate_per_1000, 2),
        "orders_possible": orders_possible,
    })


# B51: lot generator — генерация массива лотов с вариациями
@seller_bp.route("/api/dev/lots/generate", methods=["POST"])
def b51_generate_lots():
    """Генерирует список лотов для выбранной услуги Twiboost.
    Body: {
        "service_id": 4961,
        "quantity": 1000,         # размер пакета (1000 подписчиков и т.д.)
        "variations": 15,         # сколько уникальных названий
        "price": 40,              # цена в рублях
        "category_id": null       # категория FunPay (если знаем)
    }"""
    import random as _r
    body = request.get_json(silent=True) or {}
    service_id = body.get("service_id")
    quantity = int(body.get("quantity") or 1000)
    variations = int(body.get("variations") or 15)
    price = float(body.get("price") or 40)
    
    if not service_id:
        return jsonify({"ok": False, "error": "service_id required"})
    
    # Найдём услугу в кеше
    services = _b50_load_twiboost_services()
    service = None
    for s in services:
        if str(s.get("service_id")) == str(service_id):
            service = s
            break
    
    if not service:
        return jsonify({"ok": False, "error": f"service {service_id} not in cache"})
    
    platform, stype = _b50_categorize_service(service)
    svc_name = service.get("name", "")
    
    # Шаблоны названий лотов
    # {qty} {what} {platform} {tail}
    
    platform_names = {
        "telegram": ["TELEGRAM", "Telegram", "ТЕЛЕГРАМ", "Telegram TG", "TG"],
        "tiktok":   ["TIKTOK", "TikTok", "ТИКТОК", "TT"],
        "instagram":["INSTAGRAM", "Instagram", "ИНСТАГРАМ", "INST", "Инста"],
        "vk":       ["ВКОНТАКТЕ", "ВК", "VK", "Vkontakte"],
        "youtube":  ["YOUTUBE", "YouTube", "ЮТУБ", "YT"],
        "twitch":   ["TWITCH", "Twitch", "ТВИЧ"],
        "kick":     ["KICK", "Kick", "КИК"],
        "twitter":  ["TWITTER", "Twitter", "X", "ТВИТТЕР"],
        "max":      ["MAX", "Макс"],
        "rutube":   ["RUTUBE", "Rutube", "Рутуб"],
    }
    
    type_names = {
        "subscribers": ["ПОДПИСЧИКОВ", "Подписчиков", "ПОДПИСЧИКИ", "subs", "подписчики", "follow"],
        "views":       ["ПРОСМОТРОВ", "Просмотров", "ПРОСМОТРЫ", "views", "просмотры"],
        "viewers":     ["ЗРИТЕЛЕЙ", "Зрителей", "viewers"],
        "likes":       ["ЛАЙКОВ", "Лайков", "ЛАЙКИ", "likes"],
        "reactions":   ["РЕАКЦИЙ", "Реакций", "РЕАКЦИИ", "reactions"],
        "comments":    ["КОММЕНТАРИЕВ", "Комментариев", "comments"],
        "shares":      ["РЕПОСТОВ", "Репостов", "shares"],
        "premium":     ["PREMIUM", "Premium", "ПРЕМИУМ"],
        "stars":       ["ЗВЁЗД", "Звёзд", "stars"],
        "clicks":      ["КЛИКОВ", "Кликов", "clicks"],
    }
    
    emojis_start = ["🌟", "⚡", "🔥", "💥", "🎯", "🚀", "⭐", "💫", "✨", "🏆", "💎", "🎁", "📈", "✅", "🎉"]
    emojis_end   = ["⚡", "🔥", "✨", "🚀", "💎", "🎯", "📈", "💥", "🌟", "✅"]
    
    tails = [
        "БЫСТРО", "за минуту", "моментально", "качество", "ГАРАНТИЯ", "топ",
        "живые", "проверено", "без списаний", "стабильно", "10/10",
        "лучшая цена", "дешево", "СУПЕР", "PRO", "новинка",
    ]
    
    plats = platform_names.get(platform, [platform.upper()])
    types = type_names.get(stype, [stype])
    
    seen_titles = set()
    lots = []
    attempts = 0
    
    while len(lots) < variations and attempts < variations * 10:
        attempts += 1
        e1 = _r.choice(emojis_start)
        e2 = _r.choice(emojis_end)
        plat = _r.choice(plats)
        typ = _r.choice(types)
        tail = _r.choice(tails) if _r.random() < 0.6 else ""
        
        # Формат: эмодзи + qty + type + platform + (tail) + маркер
        templates = [
            f"{e1} {quantity} {typ} {plat} {e2} [AS#{service_id}]",
            f"{e1} {plat} {quantity} {typ} {tail} [AS#{service_id}]",
            f"{e1} {typ} {plat} {quantity} штук {tail} [AS#{service_id}]",
            f"{plat} {quantity} {typ} {e1}{e2} [AS#{service_id}]",
            f"{e1} {tail} {quantity} {typ} {plat} [AS#{service_id}]",
        ]
        title = _r.choice(templates).strip()
        # Уберём двойные пробелы
        title = " ".join(title.split())
        
        if title in seen_titles:
            continue
        seen_titles.add(title)
        
        # Описание
        descr_templates = [
            f"✅ {quantity} {typ} на {plat}\n⚡ Быстрая доставка\n🎯 Высокое качество\n💎 Гарантия",
            f"🌟 Накрутка {quantity} {typ}\n📈 Платформа: {plat}\n✅ Старт за 5 минут\n💯 Без списаний",
            f"⚡ {plat} — {quantity} {typ}\n🚀 Моментальное начало\n✨ Только живые\n🏆 Топовое качество",
        ]
        descr = _r.choice(descr_templates)
        
        lots.append({
            "title": title,
            "description": descr,
            "price_rub": price,
            "amount": 1,
            "marker": f"[AS#{service_id}]",
            "service_id": service_id,
            "service_name": svc_name,
            "quantity": quantity,
            "platform": platform,
            "type": stype,
        })
    
    return jsonify({
        "ok": True,
        "service_id": service_id,
        "service_name": svc_name,
        "platform": platform,
        "type": stype,
        "quantity": quantity,
        "price_rub": price,
        "variations_requested": variations,
        "lots_generated": len(lots),
        "lots": lots,
    })


@seller_bp.route("/api/dev/sandbox/confirm_order", methods=["POST"])
def b63_sandbox_confirm():
    """B63: sandbox confirm — симулирует подтверждение заказа покупателем."""
    import time as _t
    body = request.get_json(silent=True) or {}
    order_id = body.get("order_id") or "SAND_LAST"
    
    with _b35_lock:
        _b35_messages.append({
            "from": "system",
            "text": f"✅ Покупатель ПОДТВЕРДИЛ выполнение заказа #{order_id}",
            "ts": _t.time(),
        })
        _b35_save()
    
    bus = getattr(svc, "event_bus", None)
    if bus:
        bus.emit("order_completed", {
            "type": "order_completed",
            "order_id": order_id,
            "previous_status": "PAID",
            "new_status": "CLOSED",
            "chat_id": _b35_chat_id,
            "buyer": "sandbox_buyer",
            "buyer_id": 99999,
            "title": "Sandbox lot [AS#4961]",
            "lot_title": "Sandbox lot [AS#4961]",
            "_sandbox": True,
        })
    
    return jsonify({"ok": True, "order_id": order_id})


# B73: reply_to_review endpoint
@seller_bp.route("/api/seller/reviews/reply", methods=["POST"])
def b73_reply_to_review():
    """Отвечает на отзыв продавца. Body: {order_id, text}."""
    body = request.get_json(silent=True) or {}
    order_id = body.get("order_id")
    text_ = body.get("text", "")
    if not order_id:
        return jsonify({"ok": False, "error": "order_id required"})
    return jsonify(svc.reply_to_review(order_id, text_))





@seller_bp.route("/api/market/analyze_niches", methods=["POST"])
def analyze_niches():
    body = request.json or {}
    budget = float(body.get("budget", 0))
    if budget <= 0:
        return jsonify({"ok": False, "error": "Бюджет должен быть больше 0"})
    return jsonify(svc.analyze_niches_with_budget(budget))

@seller_bp.route("/api/autosmm/generate_from_niches", methods=["POST"])
def generate_from_niches():
    body = request.json or {}
    from plugins.plugin_manager import plugin_manager_singleton as pm
    plugin = pm.get_plugin("autosmm_plugin")
    if not plugin:
        return jsonify({"ok": False, "error": "Плагин AutoSMM не загружен"})
    result = plugin.action_generate_lots_from_niches(body)
    return jsonify(result)


# ==================== DEEP TWIBOOST NICHES (Этап B.2) ====================
@seller_bp.route("/api/market/analyze_niches_deep", methods=["POST"])
def analyze_niches_deep():
    """
    Запуск глубокого анализа всех Twiboost-услуг (до 1751).
    Body: { "budget": 500 }
    Returns: { "ok": true, "task_id": "abc123" } — мгновенно
    Прогресс/результат: GET /api/market/analyze_niches_deep/progress?task_id=...
    """
    import threading, uuid
    body = request.json or {}
    try:
        budget = float(body.get("budget", 0))
    except Exception:
        budget = 0
    if budget <= 0:
        return jsonify({"ok": False, "error": "Бюджет должен быть больше 0"})
    task_id = uuid.uuid4().hex[:12]

    def _run():
        try:
            svc.analyze_niches_deep(budget=budget, task_id=task_id)
        except Exception:
            import traceback
            traceback.print_exc()

    t = threading.Thread(target=_run, daemon=True, name=f"niches_deep_{task_id}")
    t.start()
    return jsonify({"ok": True, "task_id": task_id, "started": True})


@seller_bp.route("/api/market/analyze_niches_deep/progress", methods=["GET"])
def analyze_niches_deep_progress():
    """
    GET ?task_id=...
    Returns: { available, task_id, status: 'running'|'completed'|'failed', progress, total, results, error, elapsed_sec }
    """
    task_id = request.args.get("task_id", "").strip()
    if not task_id:
        return jsonify({"available": False, "error": "task_id required"})
    progress = svc.get_deep_analysis_status(task_id)
    return jsonify(progress)


# ==================== GLOBAL NICHES (Этап B) ====================
@seller_bp.route("/api/market/analyze_niches_global", methods=["POST"])
def analyze_niches_global():
    """
    Запуск глобального скана всех SMM-subcategory FunPay в фоновом потоке.
    Body: { "budget": 500, "force_refresh": false }
    Returns: { "ok": true, "task_id": "abc123" } — мгновенно
    Прогресс/результат: GET /api/market/analyze_niches_global/progress?task_id=...
    """
    import threading, uuid
    body = request.json or {}
    try:
        budget = float(body.get("budget", 0))
    except Exception:
        budget = 0
    if budget <= 0:
        return jsonify({"ok": False, "error": "Бюджет должен быть больше 0"})
    force_refresh = bool(body.get("force_refresh", False))

    task_id = uuid.uuid4().hex[:12]

    def _run():
        try:
            svc.analyze_niches_global(budget=budget, force_refresh=force_refresh, task_id=task_id)
        except Exception as e:
            import traceback
            traceback.print_exc()

    t = threading.Thread(target=_run, daemon=True, name=f"niches_global_{task_id}")
    t.start()

    return jsonify({"ok": True, "task_id": task_id, "started": True})


@seller_bp.route("/api/market/analyze_niches_global/progress", methods=["GET"])
def analyze_niches_global_progress():
    """
    GET ?task_id=...
    Returns: { available, task_id, status: 'running'|'done'|'error', current, total, percent, last_done, elapsed_sec, error, result_ready }
    Если status == 'done' — дополнительно отдаём поле "result" с полным набором ниш.
    """
    task_id = request.args.get("task_id", "").strip()
    if not task_id:
        return jsonify({"available": False, "error": "task_id required"})
    progress = svc.get_niches_global_progress(task_id)
    # Если готово — подкинем результат
    try:
        st = svc._niches_global_state.get(task_id)
        if st and st.get("result"):
            progress["result"] = st["result"]
    except Exception:
        pass
    return jsonify(progress)


@seller_bp.route("/api/seller/price/optimize", methods=["POST"])
def optimize_price():
    body = request.get_json(silent=True) or {}
    lot_id = body.get("lot_id") or request.args.get("lot_id", type=int)
    if not lot_id:
        return jsonify({"error": "lot_id required"}), 400
    try:
        return jsonify(svc.calculate_optimal_price(int(lot_id), strategy="competitive", params={}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@seller_bp.route("/api/market/optimal/<int:lot_id>/apply", methods=["POST"])
def apply_optimal(lot_id):
    try:
        result = svc.calculate_optimal_price(lot_id, strategy="competitive", params={})
        return jsonify({"ok": True, "applied": True, "lot_id": lot_id, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@seller_bp.route("/api/scheduler/suggestions")
def scheduler_suggestions():
    return jsonify({"suggestions": []})


@seller_bp.route("/api/market/twiboost/services")
def twiboost_services():
    services = _b50_load_twiboost_services()
    return jsonify({"services": services})


@seller_bp.route("/api/lots/generate", methods=["POST"])
def generate_lots_endpoint():
    if LotGenerator is None:
        return jsonify({"ok": False, "error": "LotGenerator not available"}), 500
    body = request.get_json(silent=True) or {}
    plugin = body.get("plugin", "autosmm")
    supplier = body.get("supplier", "")
    dry_run = bool(body.get("dry_run", True))

    generator = LotGenerator(seller_service=svc)
    result = {"ok": True, "plugin": plugin, "supplier": supplier, "dry_run": dry_run, "lots": []}

    if plugin == "autosmm":
        service_id = body.get("service_id")
        quantity = int(body.get("quantity") or 1000)
        variations = int(body.get("variations") or 15)
        price = float(body.get("price") or 40.0)
        if service_id:
            lots = generator.generate_lots_for_service(int(service_id), "", quantity=quantity, variations=variations, price=price)
            result["lots"] = lots
        else:
            all_lots = generator.generate_all_lots()
            result["lots"] = all_lots.get("autosmm", [])
    elif plugin == "donate":
        if supplier in ("gorgona", "holdboost"):
            months_list = [1, 3] if not body.get("months") else [int(body.get("months"))]
            lots = []
            for m in months_list:
                lots.extend(generator.generate_discord_boost_lots(supplier, months=m, variations=int(body.get("variations") or 15)))
            result["lots"] = lots
        elif supplier == "kosell":
            variations = int(body.get("variations") or 15)
            products = generator._load_kosell_products()
            result["lots"] = generator.generate_kosell_lots(products, variations=variations)
        else:
            result["lots"] = []

    if not dry_run and result["lots"]:
        save_result = generator.save_lots(result["lots"], plugin=plugin, supplier=supplier)
        result["save_result"] = save_result

    return jsonify(result)


@seller_bp.route("/api/system/simulate", methods=["POST"])
def system_simulate():
    try:
        from runtime.simulator import PluginSimulator
        sim = PluginSimulator(getattr(svc, "plugin_manager", None))
        report, all_ok = sim.run_all()
        # Симуляция — диагностическая операция. Она не вправе включать реальные
        # продажи и менять dry_run без отдельного явного действия администратора.
        return jsonify({"ok": all_ok, "report": report, "dry_run": True})
    except Exception as e:
        current_app.logger.exception("System simulation failed")
        return jsonify({"ok": False, "error": str(e)}), 500


@seller_bp.route("/api/dev/lots/deactivate_all", methods=["POST"])
def deactivate_all_lots():
    try:
        from runtime.seller_service import seller_service_singleton as svc
        lots_data = svc.get_my_lots(force_refresh=True)
        deactivated = 0
        markers = ["[AS#", "[GB#", "[HB#", "[KS#"]
        for lot in lots_data.get("lots", []):
            title = lot.get("title", "")
            if any(m in title for m in markers):
                lot_id = lot.get("id")
                if lot_id:
                    svc.toggle_lot_active(lot_id, False, dry_run=False)
                    deactivated += 1
        return jsonify({"ok": True, "deactivated": deactivated})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _toggle_lots(svc, supplier, deactivate: bool):
    lots_data = svc.get_my_lots(force_refresh=True)
    markers = ["[AS#", "[GB#", "[HB#", "[KS#"]
    toggled = 0
    for lot in lots_data.get("lots", []):
        title = lot.get("title", "")
        if not any(m in title for m in markers):
            continue
        lot_id = lot.get("id")
        if lot_id:
            svc.toggle_lot_active(lot_id, not deactivate, dry_run=False)
            toggled += 1
    return toggled


@seller_bp.route("/api/seller/lots/deactivate", methods=["POST"])
def deactivate_lots_by_supplier():
    body = request.get_json(silent=True) or {}
    supplier = body.get("supplier")
    all_lots = bool(body.get("all", False))
    if not supplier and not all_lots:
        return jsonify({"ok": False, "error": "нужен supplier или all=true"}), 400
    count = _toggle_lots(svc, None if all_lots else supplier, True)
    return jsonify({"ok": True, "deactivated": count})


@seller_bp.route("/api/seller/lots/activate", methods=["POST"])
def activate_lots_by_supplier():
    body = request.get_json(silent=True) or {}
    supplier = body.get("supplier")
    all_lots = bool(body.get("all", False))
    if not supplier and not all_lots:
        return jsonify({"ok": False, "error": "нужен supplier или all=true"}), 400
    count = _toggle_lots(svc, None if all_lots else supplier, False)
    return jsonify({"ok": True, "activated": count})


@seller_bp.route("/api/lots/create_all", methods=["POST"])
def create_all_lots():
    if LotGenerator is None:
        return jsonify({"ok": False, "error": "LotGenerator not available"}), 500
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run", False))
    try:
        generator = LotGenerator(seller_service=svc)
        all_lots = generator.generate_all_lots()
        by_section = {k: len(v) for k, v in all_lots.items()}
        flat = []
        for v in all_lots.values():
            flat.extend(v)
        created = 0
        if not dry_run and flat:
            print(f"[Endpoint] BEFORE save_lots: flat_count={len(flat)}, seller_service={svc!r}")
            import runtime.lot_generator as _lg
            print(f"[Endpoint] save_lots is {_lg.LotGenerator.save_lots}")
            res = generator.save_lots(flat, plugin="autosmm")
            print(f"[Endpoint] AFTER save_lots result={res}")
            created = res.get("created", 0)
        return jsonify({
            "ok": True, "dry_run": dry_run, "generated": len(flat),
            "created": created, "by_section": by_section,
            "_marker": "ENDPOINT_ACTUAL_v2",
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@seller_bp.route("/api/seller/balance/suppliers")
def suppliers_balance():
    try:
        from runtime.supplier_registry import SupplierRegistry
        out = {}
        for name in SupplierRegistry.get_all_suppliers():
            out[name] = {
                "balance": None,
                "enabled": SupplierRegistry.is_enabled(name),
            }
        return jsonify(out)
    except Exception:
        return jsonify({})


@seller_bp.route("/api/system/settings/auto_lots", methods=["POST"])
def toggle_auto_lots():
    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled", True))
    try:
        from plugins.autodonate_plugin import AutoDonatePlugin
        from plugins.autosmm_plugin import AutoSMMPlugin
        for plugin_cls in [AutoSMMPlugin, AutoDonatePlugin]:
            plugin = svc.plugin_manager.plugins.get(plugin_cls.__module__.split('.')[-1])
            if plugin:
                plugin.config["auto_generate_lots"] = enabled
                plugin.save_config()
    except Exception:
        pass
    return jsonify({"ok": True, "auto_lots_enabled": enabled})


@seller_bp.route("/api/system/start", methods=["POST"])
def system_start():
    """Запуск системы (для Telegram бота)"""
    return jsonify({"ok": True, "message": "Система уже запущена"})


@seller_bp.route("/api/system/stop", methods=["POST"])
def system_stop():
    """Остановка системы (для Telegram бота)"""
    return jsonify({"ok": True, "message": "Система работает в headless режиме, остановка через UI"})


@seller_bp.route("/api/ai/status")
def ai_status():
    """Статус AI агента (для Telegram бота)"""
    return jsonify({"ok": True, "status": "available", "message": "AI агент доступен через /api/ai/recommendations"})
