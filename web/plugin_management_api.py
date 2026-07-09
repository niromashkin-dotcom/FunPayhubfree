from flask import Blueprint, jsonify, request
import sys, os, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime.plugin_config_manager import PluginConfigManager
from runtime.dependency_resolver import DependencyResolver

plugin_mgmt_bp = Blueprint("plugin_management", __name__)
config_manager = PluginConfigManager()
dep_resolver = DependencyResolver()

HISTORY_FILE = Path("configs/plugin_history.json")
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _runtime_controller():
    from flask import current_app
    return getattr(current_app, "runtime_controller", None)


def _load_history():
    if not HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_history(h):
    HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_history(plugin_name, action, old_state, new_state):
    h = _load_history()
    if plugin_name not in h:
        h[plugin_name] = []
    h[plugin_name].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "from": old_state,
        "to": new_state
    })
    h[plugin_name] = h[plugin_name][-50:]
    _save_history(h)


def _get_plugins_data():
    rc = _runtime_controller()
    if rc is not None:
        result = rc.list_plugins()
        plugins_raw = result.get("data", {}).get("plugins", [])
        return plugins_raw, True
    mock = [
        {"module": "AutoResponse", "name": "AutoResponse", "version": "1.0.0", "state": "active"},
        {"module": "AutoDelivery", "name": "AutoDelivery", "version": "1.0.0", "state": "active"},
        {"module": "NewMessageView", "name": "NewMessageView", "version": "1.0.0", "state": "disabled"},
        {"module": "ProductUpdater", "name": "ProductUpdater", "version": "1.0.0", "state": "active"},
    ]
    return mock, False


@plugin_mgmt_bp.route("/api/plugins")
def get_all_plugins():
    plugins_raw, live = _get_plugins_data()
    result = []
    for p in plugins_raw:
        name = p.get("module", p.get("name", ""))
        config = config_manager.get_config(name) or config_manager.create_default_config(name)
        result.append({
            "name": name,
            "display_name": p.get("name", name),
            "version": p.get("version", "0.0.0"),
            "state": p.get("state", "unknown"),
            "enabled": config.get("enabled", False),
            "priority": config.get("priority", 10),
            "cpu": 0.0,
            "memory": 0.0,
            "events": 0,
            "dependencies": dep_resolver.get_dependencies(name),
            "dependents": dep_resolver.get_dependents(name),
            "can_disable": True,
            "can_enable": True,
            "live": live
        })
    return jsonify({"plugins": result})


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>")
def get_plugin_details(plugin_name):
    rc = _runtime_controller()
    if rc is not None:
        info_result = rc.get_plugin_info(plugin_name)
        if not info_result.get("success"):
            return jsonify({"error": "Plugin not found"}), 404
        data = info_result.get("data", {})
        state = info_result.get("state", "unknown")
    else:
        data = {"name": plugin_name, "version": "0.0.0", "config": {}}
        state = "unknown"
    config = config_manager.get_config(plugin_name) or config_manager.create_default_config(plugin_name)
    history = _load_history().get(plugin_name, [])
    return jsonify({
        "name": plugin_name,
        "state": state,
        "config": config,
        "dependencies": dep_resolver.get_dependencies(plugin_name),
        "dependents": dep_resolver.get_dependents(plugin_name),
        "history": history[-20:],
        "metrics": {"cpu": 0.0, "memory": 0.0, "events": 0}
    })


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/enable", methods=["POST"])
def enable_plugin(plugin_name):
    rc = _runtime_controller()
    old_state = "unknown"
    if rc is not None:
        old_state = rc.get_plugin_state(plugin_name).get("state", "unknown")
        result = rc.enable_plugin(plugin_name)
        if not result.get("success"):
            return jsonify({"error": result.get("message", "Failed")}), 400
        new_state = result.get("state", "active")
    else:
        new_state = "active"
    config = config_manager.get_config(plugin_name) or config_manager.create_default_config(plugin_name)
    config["enabled"] = True
    config_manager.update_config(plugin_name, config)
    _record_history(plugin_name, "enable", old_state, new_state)
    return jsonify({"status": "enabled", "plugin": plugin_name, "state": new_state})


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/disable", methods=["POST"])
def disable_plugin(plugin_name):
    rc = _runtime_controller()
    old_state = "unknown"
    if rc is not None:
        old_state = rc.get_plugin_state(plugin_name).get("state", "unknown")
        result = rc.disable_plugin(plugin_name)
        if not result.get("success"):
            return jsonify({"error": result.get("message", "Failed")}), 400
        new_state = result.get("state", "disabled")
    else:
        new_state = "disabled"
    config = config_manager.get_config(plugin_name) or config_manager.create_default_config(plugin_name)
    config["enabled"] = False
    config_manager.update_config(plugin_name, config)
    _record_history(plugin_name, "disable", old_state, new_state)
    return jsonify({"status": "disabled", "plugin": plugin_name, "state": new_state})


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/restart", methods=["POST"])
def restart_plugin(plugin_name):
    rc = _runtime_controller()
    old_state = "unknown"
    if rc is not None:
        old_state = rc.get_plugin_state(plugin_name).get("state", "unknown")
        result = rc.restart_plugin(plugin_name)
        if not result.get("success"):
            return jsonify({"error": result.get("message", "Failed")}), 400
        new_state = result.get("state", "active")
    else:
        new_state = "active"
    _record_history(plugin_name, "restart", old_state, new_state)
    return jsonify({"status": "restarted", "plugin": plugin_name, "state": new_state})


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/config")
def get_plugin_config(plugin_name):
    config = config_manager.get_config(plugin_name) or config_manager.create_default_config(plugin_name)
    return jsonify({"config": config})


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/config", methods=["PUT"])
def update_plugin_config(plugin_name):
    new_config = request.json
    is_valid, message = config_manager.validate_config(plugin_name, new_config)
    if not is_valid:
        return jsonify({"error": message}), 400
    success = config_manager.update_config(plugin_name, new_config)
    if success:
        rc = _runtime_controller()
        if rc is not None:
            rc.reload_plugin_config(plugin_name)
        return jsonify({"status": "updated", "config": new_config})
    return jsonify({"error": "Failed to update config"}), 500


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/history")
def get_plugin_history(plugin_name):
    history = _load_history().get(plugin_name, [])
    return jsonify({"history": history})


@plugin_mgmt_bp.route("/api/plugins/dependencies")
def get_dependency_graph():
    return jsonify({
        "graph": dep_resolver.get_dependency_graph(),
        "load_order": dep_resolver.get_load_order()
    })

# =====================================================================
# AUTO-UI: schema + actions endpoints
# =====================================================================

@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/schema")
def get_plugin_schema(plugin_name):
    """Return CONFIG_SCHEMA declared in plugin class.
    Used by UI to auto-render settings form."""
    from flask import current_app
    rc = getattr(current_app, "runtime_controller", None)
    if rc is None:
        return jsonify({"schema": [], "error": "no runtime"}), 200

    pm = getattr(rc, "_plugin_manager", None)
    if pm is None:
        return jsonify({"schema": [], "error": "no plugin manager"}), 200

    plugin = pm.plugins.get(plugin_name)
    if plugin is None:
        return jsonify({"schema": [], "error": "plugin not found"}), 404

    schema = getattr(plugin.__class__, "CONFIG_SCHEMA", None)
    if schema is None:
        schema = []

    # Current config
    cfg = config_manager.get_config(plugin_name) or {}

    return jsonify({
        "schema": schema,
        "config": cfg,
        "plugin_info": plugin.get_info(),
    })


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/action/<action_name>", methods=["POST"])
def call_plugin_action(plugin_name, action_name):
    """Call a custom action exposed by plugin.
    Plugin must have method `action_<name>(payload) -> dict`."""
    from flask import current_app
    rc = getattr(current_app, "runtime_controller", None)
    if rc is None:
        return jsonify({"ok": False, "error": "no runtime"}), 400

    pm = getattr(rc, "_plugin_manager", None)
    if pm is None:
        return jsonify({"ok": False, "error": "no plugin manager"}), 400

    plugin = pm.plugins.get(plugin_name)
    if plugin is None:
        return jsonify({"ok": False, "error": "plugin not found"}), 404

    method = getattr(plugin, f"action_{action_name}", None)
    if method is None or not callable(method):
        return jsonify({"ok": False, "error": f"action {action_name} not found"}), 404

    try:
        payload = request.json or {}
        result = method(payload)
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/logs")
def get_plugin_logs(plugin_name):
    """Return recent logs/stats from plugin.
    Plugin should expose `get_stats()` or `get_logs()`."""
    from flask import current_app
    rc = getattr(current_app, "runtime_controller", None)
    if rc is None:
        return jsonify({"logs": [], "stats": {}}), 200

    pm = getattr(rc, "_plugin_manager", None)
    if pm is None:
        return jsonify({"logs": [], "stats": {}}), 200

    plugin = pm.plugins.get(plugin_name)
    if plugin is None:
        return jsonify({"logs": [], "stats": {}}), 404

    stats = {}
    if hasattr(plugin, "get_stats"):
        try:
            stats = plugin.get_stats() or {}
        except Exception:
            pass

    logs = []
    if hasattr(plugin, "get_logs"):
        try:
            logs = plugin.get_logs() or []
        except Exception:
            pass

    return jsonify({"stats": stats, "logs": logs})


@plugin_mgmt_bp.route("/api/plugins/<plugin_name>/reset", methods=["POST"])
def reset_plugin_config(plugin_name):
    """Reset plugin config to schema defaults."""
    from flask import current_app
    rc = getattr(current_app, "runtime_controller", None)

    schema = []
    if rc:
        pm = getattr(rc, "_plugin_manager", None)
        if pm:
            plugin = pm.plugins.get(plugin_name)
            if plugin:
                schema = getattr(plugin.__class__, "CONFIG_SCHEMA", []) or []

    default_config = {"priority": 10, "enabled": False}
    for field in schema:
        key = field.get("key")
        if key:
            default_config[key] = field.get("default")

    config_manager.update_config(plugin_name, default_config)
    if rc:
        rc.reload_plugin_config(plugin_name)
    return jsonify({"ok": True, "config": default_config})


@plugin_mgmt_bp.route("/api/plugins/autostart", methods=["GET", "POST"])
def plugins_autostart():
    cfg_path = Path("configs/plugin_autostart.json")
    if request.method == "GET":
        if cfg_path.exists():
            try:
                return jsonify(json.loads(cfg_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return jsonify({})
    body = request.get_json(silent=True) or {}
    cfg_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"ok": True})