window.projectMapData = [
  {
    "module": "runtime.ai_engineer_agent",
    "cluster": "Core Runtime",
    "file_path": "runtime/ai_engineer_agent.py",
    "classes": [
      {
        "name": "AIEngineerAgent",
        "methods": [
          "__init__",
          "start",
          "stop",
          "_start_scanner",
          "_scan_logs",
          "_analyze_errors",
          "_simple_fix_suggestion",
          "_propose_patch",
          "apply_patch",
          "_send_admin"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "re",
      "time",
      "json",
      "threading",
      "logging",
      "pathlib",
      "typing",
      "datetime"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.ai_team_orchestrator",
    "cluster": "Core Runtime",
    "file_path": "runtime/ai_team_orchestrator.py",
    "classes": [
      {
        "name": "LogMonitor",
        "methods": [
          "__init__",
          "collect_errors",
          "_scan_file"
        ]
      },
      {
        "name": "TaskManager",
        "methods": [
          "__init__",
          "_load_tasks",
          "_save_tasks",
          "create_task",
          "_get_context"
        ]
      },
      {
        "name": "AITeamOrchestrator",
        "methods": [
          "__init__",
          "run_once",
          "_apply_safe_fix"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "os",
      "re",
      "subprocess",
      "time",
      "datetime",
      "pathlib",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.__init__"
    ]
  },
  {
    "module": "runtime.autoreply_engine",
    "cluster": "Core Runtime",
    "file_path": "runtime/autoreply_engine.py",
    "classes": [
      {
        "name": "ChatLockRegistry",
        "methods": [
          "__init__",
          "acquire",
          "release",
          "is_locked",
          "owner"
        ]
      },
      {
        "name": "AutoReplyEngine",
        "methods": [
          "__init__",
          "_is_processed_by_autosmm",
          "subscribe",
          "_load_rules",
          "_load_templates",
          "_resolve_template",
          "_sent_log_path",
          "_load_sent_log",
          "_save_sent_log",
          "_is_recent",
          "_send",
          "_render",
          "_on_new_message",
          "_on_new_order",
          "_on_review"
        ]
      }
    ],
    "functions": [
      "_project_root",
      "_configs_dir"
    ],
    "imports": [
      "json",
      "time",
      "threading",
      "pathlib",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.backup_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/backup_manager.py",
    "classes": [
      {
        "name": "BackupManager",
        "methods": [
          "__init__",
          "start",
          "stop",
          "backup_now",
          "restore",
          "list_backups",
          "_start_daily_backup"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "time",
      "shutil",
      "threading",
      "logging",
      "pathlib",
      "datetime",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.context",
    "cluster": "Core Runtime",
    "file_path": "runtime/context.py",
    "classes": [
      {
        "name": "AppContext",
        "methods": [
          "__init__",
          "set_runtime_controller",
          "set_event_bus",
          "set_websocket_hub",
          "set_snapshot_builder",
          "update_snapshot",
          "get_snapshot",
          "get_runtime_controller",
          "get_event_bus",
          "get_websocket_hub"
        ]
      }
    ],
    "functions": [
      "get_app_context"
    ],
    "imports": [],
    "depends_on": [],
    "used_by": [
      "runtime.snapshot_builder"
    ]
  },
  {
    "module": "runtime.dependency_resolver",
    "cluster": "Core Runtime",
    "file_path": "runtime/dependency_resolver.py",
    "classes": [
      {
        "name": "PluginDependency",
        "methods": []
      },
      {
        "name": "DependencyResolver",
        "methods": [
          "__init__",
          "register_plugin",
          "get_dependencies",
          "get_dependents",
          "can_disable",
          "can_enable",
          "get_dependency_graph",
          "get_load_order"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "typing",
      "dataclasses"
    ],
    "depends_on": [],
    "used_by": [
      "web.plugin_management_api"
    ]
  },
  {
    "module": "runtime.emergency_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/emergency_manager.py",
    "classes": [
      {
        "name": "EmergencyManager",
        "methods": [
          "__init__",
          "state",
          "is_normal",
          "is_emergency",
          "start",
          "stop",
          "check_supplier",
          "check_cancel_rate",
          "emergency_stop",
          "resume",
          "_set_state",
          "_deactivate_supplier",
          "_deactivate_all_lots",
          "_activate_all_lots",
          "_notify_admin",
          "_get_bot_token",
          "to_dict"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "logging",
      "threading",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.event_bus",
    "cluster": "Core Runtime",
    "file_path": "runtime/event_bus.py",
    "classes": [
      {
        "name": "EventAction",
        "methods": []
      },
      {
        "name": "EventResult",
        "methods": []
      },
      {
        "name": "EventSource",
        "methods": []
      },
      {
        "name": "EventSeverity",
        "methods": []
      },
      {
        "name": "Event",
        "methods": [
          "__post_init__",
          "to_dict"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "uuid",
      "dataclasses",
      "enum"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.event_types",
    "cluster": "Core Runtime",
    "file_path": "runtime/event_types.py",
    "classes": [
      {
        "name": "EventAction",
        "methods": []
      },
      {
        "name": "EventResult",
        "methods": []
      },
      {
        "name": "EventSource",
        "methods": []
      },
      {
        "name": "EventSeverity",
        "methods": []
      },
      {
        "name": "Event",
        "methods": [
          "__post_init__",
          "to_dict"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "uuid",
      "dataclasses",
      "enum"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.observability.observability_hub",
      "runtime.websocket.websocket_hub",
      "runtime.__init__",
      "runtime.websocket.event_serializer",
      "runtime.runtime_controller",
      "runtime.observability.event_store"
    ]
  },
  {
    "module": "runtime.funpay_catalog",
    "cluster": "Core Runtime",
    "file_path": "runtime/funpay_catalog.py",
    "classes": [],
    "functions": [
      "_ensure_dir",
      "fetch_all_subcategories",
      "get_cached"
    ],
    "imports": [
      "__future__",
      "os",
      "re",
      "json",
      "time",
      "typing",
      "runtime.http_client"
    ],
    "depends_on": [
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "runtime.http_client",
    "cluster": "Core Runtime",
    "file_path": "runtime/http_client.py",
    "classes": [
      {
        "name": "HTTPClientError",
        "methods": [
          "__init__",
          "_format"
        ]
      },
      {
        "name": "HTTPClient",
        "methods": [
          "__init__",
          "get",
          "post",
          "put",
          "delete",
          "_request",
          "_parse_response",
          "_sleep",
          "close",
          "__enter__",
          "__exit__"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "logging",
      "random",
      "time",
      "typing",
      "requests",
      "requests.adapters",
      "urllib3.util.retry"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.telegram_notifier_plugin",
      "web.funpay_proxy",
      "runtime.notification_manager",
      "runtime.ai_team.model_manager",
      "runtime.order_tracker",
      "web.assistant_api",
      "plugins.autobump_plugin",
      "runtime.notifications.channels.discord_channel",
      "plugins.autodonate_plugin",
      "runtime.supplier_registry",
      "plugins.stars_plugin",
      "runtime.funpay_catalog",
      "hub_bootstrap",
      "plugins.autosmm_plugin"
    ]
  },
  {
    "module": "runtime.lot_generator",
    "cluster": "Core Runtime",
    "file_path": "runtime/lot_generator.py",
    "classes": [
      {
        "name": "LotGenerator",
        "methods": [
          "__init__",
          "_calculate_copies",
          "_calculate_market_price",
          "_load_return_policy",
          "_load_synonyms",
          "_load_emojis",
          "_load_twiboost_services",
          "_load_kosell_products",
          "_categorize_service",
          "_mutate_title",
          "generate_lots_for_service",
          "_make_descr",
          "generate_discord_boost_lots",
          "generate_kosell_lots",
          "generate_stars_lots",
          "generate_all_lots",
          "save_lots"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "json",
      "random",
      "itertools",
      "pathlib",
      "typing",
      "logging"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.lot_matcher",
    "cluster": "Core Runtime",
    "file_path": "runtime/lot_matcher.py",
    "classes": [],
    "functions": [
      "_normalize",
      "_extract_quantities",
      "_text_similarity",
      "match_lot_to_service",
      "classify_match",
      "auto_build_mapping"
    ],
    "imports": [
      "__future__",
      "re",
      "difflib",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.monitor_mode",
    "cluster": "Core Runtime",
    "file_path": "runtime/monitor_mode.py",
    "classes": [
      {
        "name": "RealOrderMonitor",
        "methods": [
          "__init__",
          "is_enabled",
          "start",
          "stop",
          "_on_new_order",
          "_on_order_completed",
          "_on_order_failed",
          "_classify",
          "_plan_scenario",
          "get_active_orders"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "logging",
      "os",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.notification_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/notification_manager.py",
    "classes": [
      {
        "name": "NotificationManager",
        "methods": [
          "__init__",
          "_log",
          "send_admin_notification",
          "send_user_notification",
          "send_discord_notification",
          "send_order_status_notification",
          "send_error_notification"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "logging",
      "typing",
      "runtime.http_client"
    ],
    "depends_on": [
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "runtime.order_flow",
    "cluster": "Order Engine",
    "file_path": "runtime/order_flow.py",
    "classes": [
      {
        "name": "OrderFlowManager",
        "methods": [
          "__init__",
          "start",
          "stop",
          "_on_new_order",
          "_on_order_cancelled",
          "_handle_low_balance",
          "_check_supplier_balance",
          "_deactivate_supplier_lots",
          "_on_new_message",
          "_send_order_to_supplier",
          "_process_timeouts",
          "_do_auto_refund",
          "on_order_completed",
          "on_order_confirmed",
          "_on_review",
          "_has_valid_complaint",
          "_file_unfair_review_complaint",
          "_extract_tag",
          "_tag_to_supplier",
          "_looks_like_link",
          "_find_order_by_chat",
          "_update_step",
          "_send_to_chat",
          "_send_admin",
          "_db_create_order",
          "_db_update_order",
          "_db_create_review",
          "_start_worker"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "threading",
      "logging",
      "typing",
      "pathlib",
      "runtime.messages.message_manager",
      "runtime.messages.scenario",
      "runtime.messages.order_messages",
      "runtime.messages.error_messages",
      "runtime.messages.review_messages",
      "runtime.messages.notification_messages",
      "runtime.messages.recovery_messages",
      "runtime.real_mode"
    ],
    "depends_on": [
      "runtime.messages.scenario",
      "runtime.messages.notification_messages",
      "runtime.messages.recovery_messages",
      "runtime.real_mode",
      "runtime.messages.message_manager",
      "runtime.messages.order_messages",
      "runtime.messages.review_messages",
      "runtime.messages.error_messages"
    ],
    "used_by": []
  },
  {
    "module": "runtime.order_tracker",
    "cluster": "Order Engine",
    "file_path": "runtime/order_tracker.py",
    "classes": [
      {
        "name": "OrderPaymentTracker",
        "methods": [
          "__init__",
          "set_message_manager",
          "start",
          "stop",
          "_start_worker",
          "_process_action",
          "_send_timeout_warning",
          "_do_refund",
          "_send_tg",
          "_on_new_order",
          "check_balance_filled",
          "send_refund"
        ]
      },
      {
        "name": "SupplierOrderRegistry",
        "methods": [
          "__init__",
          "is_registered",
          "get_supplier_order_id",
          "register",
          "remove",
          "_load",
          "_save"
        ]
      }
    ],
    "functions": [
      "_project_root",
      "_tg_config",
      "get_tracker",
      "get_supplier_order_registry"
    ],
    "imports": [
      "json",
      "time",
      "threading",
      "runtime.http_client",
      "pathlib",
      "typing",
      "runtime.messages.message_manager",
      "runtime.messages.order_messages",
      "runtime.messages.error_messages",
      "runtime.messages.notification_messages"
    ],
    "depends_on": [
      "runtime.http_client",
      "runtime.messages.notification_messages",
      "runtime.messages.message_manager",
      "runtime.messages.order_messages",
      "runtime.messages.error_messages"
    ],
    "used_by": [
      "plugins.autodonate_plugin",
      "plugins.autosmm_plugin",
      "plugins.stars_plugin"
    ]
  },
  {
    "module": "runtime.plugin_config_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/plugin_config_manager.py",
    "classes": [
      {
        "name": "PluginConfigManager",
        "methods": [
          "__init__",
          "load_all_configs",
          "get_config",
          "update_config",
          "create_default_config",
          "validate_config"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "os",
      "typing",
      "pathlib"
    ],
    "depends_on": [],
    "used_by": [
      "web.plugin_management_api"
    ]
  },
  {
    "module": "runtime.plugin_markers",
    "cluster": "Core Runtime",
    "file_path": "runtime/plugin_markers.py",
    "classes": [],
    "functions": [
      "parse_marker",
      "parse_all_markers",
      "has_any_marker",
      "has_marker_for",
      "strip_markers",
      "make_marker"
    ],
    "imports": [
      "re",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.price_monitor",
    "cluster": "Core Runtime",
    "file_path": "runtime/price_monitor.py",
    "classes": [],
    "functions": [
      "auto_adjust_prices"
    ],
    "imports": [
      "time",
      "pathlib"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.real_mode",
    "cluster": "Core Runtime",
    "file_path": "runtime/real_mode.py",
    "classes": [
      {
        "name": "RealModeConstraints",
        "methods": [
          "__init__",
          "is_enabled",
          "check_order",
          "require_manual_delivery",
          "get_stats"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "logging",
      "os",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow"
    ]
  },
  {
    "module": "runtime.report_engine",
    "cluster": "Core Runtime",
    "file_path": "runtime/report_engine.py",
    "classes": [
      {
        "name": "ReportEngine",
        "methods": [
          "__init__",
          "start",
          "stop",
          "_start_scheduler",
          "send_daily_report",
          "send_evening_summary",
          "send_report_on_demand",
          "_build_daily_report",
          "_build_forecast",
          "_get_main_menu_markup",
          "_send_admin"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "threading",
      "logging",
      "datetime",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.runtime_controller",
    "cluster": "Core Runtime",
    "file_path": "runtime/runtime_controller.py",
    "classes": [
      {
        "name": "RuntimeController",
        "methods": [
          "__init__",
          "set_observability_hub",
          "_emit_event",
          "_log_operation",
          "_get_health_status",
          "_get_plugins_list",
          "_build_response",
          "enable_plugin",
          "disable_plugin",
          "restart_plugin",
          "reload_plugin_config",
          "list_plugins",
          "get_plugin_info",
          "get_plugin_state",
          "get_all_states",
          "get_plugins",
          "get_runtime_status",
          "get_runtime_info",
          "get_runtime_health",
          "get_system_snapshot",
          "shutdown_runtime",
          "get_runtime_logs",
          "get_runtime_logs_count",
          "clear_runtime_logs",
          "get_health_score",
          "get_detailed_health",
          "get_plugin_metrics",
          "get_event_history",
          "get_correlation_events",
          "get_observability_stats"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "uuid",
      "typing",
      "plugins.plugin_manager",
      "runtime.runtime_log",
      "eventbus",
      "runtime.event_types"
    ],
    "depends_on": [
      "runtime.event_types",
      "plugins.plugin_manager",
      "runtime.runtime_log"
    ],
    "used_by": [
      "runtime.__init__"
    ]
  },
  {
    "module": "runtime.runtime_log",
    "cluster": "Core Runtime",
    "file_path": "runtime/runtime_log.py",
    "classes": [
      {
        "name": "LogLevel",
        "methods": []
      },
      {
        "name": "RuntimeLogEntry",
        "methods": [
          "__init__",
          "to_dict",
          "__str__"
        ]
      },
      {
        "name": "RuntimeLog",
        "methods": [
          "__init__",
          "add",
          "info",
          "warning",
          "error",
          "debug",
          "get_entries",
          "get_all",
          "get_last",
          "clear",
          "count",
          "get_by_source"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "typing",
      "enum",
      "collections"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.__init__",
      "web.logs_api",
      "runtime.runtime_controller"
    ]
  },
  {
    "module": "runtime.seller_service",
    "cluster": "Core Runtime",
    "file_path": "runtime/seller_service.py",
    "classes": [
      {
        "name": "SellerService",
        "methods": [
          "__init__",
          "_emit_event",
          "_match_order_to_lot",
          "load_credentials",
          "save_credentials",
          "clear_credentials",
          "_reset_state",
          "has_credentials",
          "_get_account",
          "_cached",
          "_set_cache",
          "_find_any_lot_id",
          "_detect_currency_from_balance",
          "get_account_overview",
          "get_balance",
          "get_my_lots",
          "get_lot_details",
          "update_lot_price",
          "toggle_lot_active",
          "bulk_update_prices",
          "raise_category_lots",
          "get_sales_data",
          "get_orders_data",
          "get_chat_messages",
          "send_chat_message",
          "reply_to_review",
          "refund_order",
          "get_customers_data",
          "get_customer_details",
          "get_balance_full",
          "_balance_history_file",
          "_load_balance_history",
          "_save_balance_snapshot",
          "get_balance_history",
          "clear_balance_history",
          "_notifications_file",
          "_state_file",
          "_load_notifications",
          "_save_notifications",
          "_load_state",
          "_save_state",
          "_b60_emit_order_completed",
          "collect_account_notifications",
          "_collect_account_notifications_impl",
          "_collect_new_reviews",
          "get_account_notifications",
          "ack_account_notification",
          "dismiss_account_notification",
          "clear_account_notifications",
          "get_my_categories",
          "scan_market",
          "compare_my_prices",
          "calculate_optimal_price",
          "simulate_price",
          "optimize_all_lots",
          "_watchlist_file",
          "_competitor_history_file",
          "_load_watchlist",
          "_save_watchlist",
          "get_competitors",
          "track_competitor",
          "untrack_competitor",
          "get_watchlist",
          "get_competitor_details",
          "_calc_heat",
          "analyze_heatmap",
          "find_niches",
          "compare_niche_with_mine",
          "_suppliers_file",
          "_lot_suppliers_file",
          "_load_suppliers_db",
          "_save_suppliers_db",
          "get_suppliers",
          "add_supplier",
          "delete_supplier",
          "get_supplier_by_id",
          "link_lot_to_supplier",
          "unlink_lot",
          "get_lot_suppliers",
          "_margin_settings_file",
          "get_margin_settings",
          "save_margin_settings",
          "calculate_margin",
          "get_margin_overview",
          "_parse_seller_profile",
          "analyze_seller_ratings",
          "get_seller_details",
          "_market_alerts_file",
          "_market_snapshot_file",
          "_alert_settings_file",
          "_load_market_alerts",
          "_save_market_alerts",
          "_load_market_snapshot",
          "_save_market_snapshot",
          "get_alert_settings",
          "save_alert_settings",
          "collect_market_alerts",
          "get_market_alerts",
          "ack_market_alert",
          "dismiss_market_alert",
          "clear_market_alerts",
          "_templates_file",
          "_rules_file",
          "_autoreply_log_file",
          "_load_templates",
          "_save_templates",
          "_load_rules",
          "_save_rules",
          "_load_autoreply_log",
          "_save_autoreply_log",
          "get_templates",
          "add_template",
          "delete_template",
          "get_autoreply_rules",
          "save_autoreply_rule",
          "delete_autoreply_rule",
          "toggle_autoreply_rule",
          "_render_template",
          "preview_template",
          "send_autoreply_test",
          "get_autoreply_log",
          "clear_autoreply_log",
          "_ad_dir",
          "_ad_settings_file",
          "_ad_bindings_file",
          "_ad_delivered_file",
          "_ad_stock_file",
          "get_autodelivery_settings",
          "save_autodelivery_settings",
          "_load_bindings",
          "_save_bindings",
          "get_autodelivery_bindings",
          "save_binding",
          "delete_binding",
          "_load_stock",
          "_save_stock",
          "get_stock",
          "add_stock_items",
          "remove_stock_item",
          "clear_stock",
          "_load_delivered",
          "_save_delivered",
          "get_delivery_log",
          "clear_delivery_log",
          "_find_binding_for_lot",
          "_is_order_delivered",
          "process_autodelivery_once",
          "_automation_file",
          "_automation_log_file",
          "_default_tasks",
          "_load_automation_tasks",
          "_save_automation_tasks",
          "_load_automation_log",
          "_save_automation_log",
          "get_automation_tasks",
          "save_automation_task",
          "toggle_automation_task",
          "run_automation_task",
          "_run_deactivate_empty",
          "_run_raise_lots",
          "get_automation_log",
          "clear_automation_log",
          "reset_automation_tasks",
          "_backup_targets",
          "create_backup",
          "list_backups",
          "restore_backup",
          "delete_backup",
          "get_backup_file_path",
          "check_system_health",
          "generate_ai_recommendations",
          "analyze_niches_with_budget",
          "test_connection",
          "analyze_niches_global",
          "get_niches_global_progress",
          "_get_all_twiboost_services",
          "_search_funpay_for_service",
          "_analyze_and_filter_niche",
          "_process_single_twiboost_service",
          "analyze_niches_deep",
          "get_deep_analysis_status",
          "create_lot"
        ]
      }
    ],
    "functions": [
      "_force_no_proxy",
      "_safe_error",
      "_currency_to_symbol"
    ],
    "imports": [
      "json",
      "time",
      "threading",
      "sys",
      "os",
      "re",
      "uuid",
      "concurrent.futures",
      "pathlib",
      "typing",
      "logging"
    ],
    "depends_on": [],
    "used_by": [
      "web.seller_api"
    ]
  },
  {
    "module": "runtime.simulator",
    "cluster": "Core Runtime",
    "file_path": "runtime/simulator.py",
    "classes": [
      {
        "name": "PluginSimulator",
        "methods": [
          "__init__",
          "run_all"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.snapshot_builder",
    "cluster": "Core Runtime",
    "file_path": "runtime/snapshot_builder.py",
    "classes": [
      {
        "name": "SnapshotBuilder",
        "methods": [
          "__init__",
          "build_snapshot",
          "refresh_snapshot"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "runtime.context"
    ],
    "depends_on": [
      "runtime.context"
    ],
    "used_by": []
  },
  {
    "module": "runtime.supplier_registry",
    "cluster": "Core Runtime",
    "file_path": "runtime/supplier_registry.py",
    "classes": [
      {
        "name": "SupplierRegistry",
        "methods": [
          "get_all_suppliers",
          "get_supplier",
          "get_enabled_suppliers",
          "get_api_key",
          "is_enabled",
          "get_marker"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "json",
      "typing",
      "runtime.http_client"
    ],
    "depends_on": [
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "runtime.supplier_worker",
    "cluster": "Core Runtime",
    "file_path": "runtime/supplier_worker.py",
    "classes": [
      {
        "name": "SupplierWorker",
        "methods": [
          "__init__",
          "start",
          "stop",
          "submit",
          "active",
          "_run"
        ]
      },
      {
        "name": "SupplierWorkerPool",
        "methods": [
          "__init__",
          "get_worker",
          "submit",
          "stop_all",
          "active_workers"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "queue",
      "threading",
      "logging",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.ttl_cache",
    "cluster": "Core Runtime",
    "file_path": "runtime/ttl_cache.py",
    "classes": [
      {
        "name": "TTLSet",
        "methods": [
          "__init__",
          "add",
          "__contains__",
          "discard",
          "_cleanup"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "threading",
      "time",
      "collections"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.version",
    "cluster": "Core Runtime",
    "file_path": "runtime/version.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.runtime_log",
      "runtime.runtime_controller",
      "runtime.event_types",
      "runtime.observability.observability_hub",
      "runtime.observability.event_store",
      "runtime.observability.metrics",
      "runtime.observability.health_engine",
      "runtime.websocket.websocket_hub",
      "runtime.ai_team_orchestrator",
      "runtime.ai_team.ai_team_orchestrator",
      "runtime.ai_team.model_manager",
      "runtime.ai_team.scheduled_tasks"
    ],
    "depends_on": [
      "runtime.event_types",
      "runtime.observability.health_engine",
      "runtime.ai_team.model_manager",
      "runtime.runtime_log",
      "runtime.observability.observability_hub",
      "runtime.websocket.websocket_hub",
      "runtime.ai_team.ai_team_orchestrator",
      "runtime.ai_team.scheduled_tasks",
      "runtime.observability.metrics",
      "runtime.runtime_controller",
      "runtime.observability.event_store",
      "runtime.ai_team_orchestrator"
    ],
    "used_by": []
  },
  {
    "module": "runtime.ai_team.ai_team_orchestrator",
    "cluster": "AI",
    "file_path": "runtime/ai_team/ai_team_orchestrator.py",
    "classes": [
      {
        "name": "AITeamOrchestrator",
        "methods": [
          "__init__",
          "_load_config",
          "analyze_error",
          "run_24_7"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "logging",
      "re",
      "threading",
      "time",
      "typing",
      "runtime.ai_team.model_manager"
    ],
    "depends_on": [
      "runtime.ai_team.model_manager"
    ],
    "used_by": [
      "runtime.ai_team.__init__",
      "runtime.__init__"
    ]
  },
  {
    "module": "runtime.ai_team.model_manager",
    "cluster": "AI",
    "file_path": "runtime/ai_team/model_manager.py",
    "classes": [
      {
        "name": "AIModelManager",
        "methods": [
          "__init__",
          "_load_config",
          "_resolve_api_key",
          "query",
          "_query_groq",
          "_query_google",
          "_query_openrouter"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "logging",
      "pathlib",
      "typing",
      "runtime.http_client",
      "security.secrets_manager"
    ],
    "depends_on": [
      "runtime.http_client",
      "security.secrets_manager"
    ],
    "used_by": [
      "runtime.ai_team.__init__",
      "runtime.__init__",
      "runtime.ai_team.ai_team_orchestrator"
    ]
  },
  {
    "module": "runtime.ai_team.scheduled_tasks",
    "cluster": "AI",
    "file_path": "runtime/ai_team/scheduled_tasks.py",
    "classes": [
      {
        "name": "ScheduledTasks",
        "methods": [
          "__init__",
          "market_analysis",
          "code_review",
          "generate_daily_report"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "logging",
      "datetime",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.ai_team.__init__",
      "runtime.__init__"
    ]
  },
  {
    "module": "runtime.ai_team.__init__",
    "cluster": "AI",
    "file_path": "runtime/ai_team/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.ai_team.ai_team_orchestrator",
      "runtime.ai_team.model_manager",
      "runtime.ai_team.scheduled_tasks"
    ],
    "depends_on": [
      "runtime.ai_team.scheduled_tasks",
      "runtime.ai_team.model_manager",
      "runtime.ai_team.ai_team_orchestrator"
    ],
    "used_by": []
  },
  {
    "module": "runtime.automation.approval_manager",
    "cluster": "AI",
    "file_path": "runtime/automation/approval_manager.py",
    "classes": [
      {
        "name": "ApprovalManager",
        "methods": [
          "__init__",
          "request_approval",
          "approve",
          "is_approved"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "pathlib",
      "datetime"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.automation.execution_history",
    "cluster": "AI",
    "file_path": "runtime/automation/execution_history.py",
    "classes": [
      {
        "name": "ExecutionHistory",
        "methods": [
          "__init__",
          "log",
          "get_last"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "pathlib",
      "datetime",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.automation.patch_executor",
    "cluster": "AI",
    "file_path": "runtime/automation/patch_executor.py",
    "classes": [
      {
        "name": "PatchExecutor",
        "methods": [
          "__init__",
          "apply"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "shutil",
      "tempfile",
      "pathlib",
      "datetime",
      "typing",
      "task_package",
      "patch_validator"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.automation.patch_validator",
    "cluster": "AI",
    "file_path": "runtime/automation/patch_validator.py",
    "classes": [
      {
        "name": "PatchValidator",
        "methods": [
          "__init__",
          "validate_files",
          "syntax_check"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "subprocess",
      "sys",
      "tempfile",
      "pathlib",
      "typing",
      "task_package"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.automation.rollback_manager",
    "cluster": "AI",
    "file_path": "runtime/automation/rollback_manager.py",
    "classes": [
      {
        "name": "RollbackManager",
        "methods": [
          "__init__",
          "rollback"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "shutil",
      "pathlib",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.automation.task_package",
    "cluster": "AI",
    "file_path": "runtime/automation/task_package.py",
    "classes": [
      {
        "name": "FileChange",
        "methods": []
      },
      {
        "name": "TaskPackage",
        "methods": [
          "to_dict",
          "from_dict",
          "save",
          "load"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "dataclasses",
      "typing",
      "datetime"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.automation.__init__",
    "cluster": "AI",
    "file_path": "runtime/automation/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "task_package",
      "patch_validator",
      "patch_executor",
      "rollback_manager",
      "approval_manager",
      "execution_history"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.backup.backup_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/backup/backup_manager.py",
    "classes": [
      {
        "name": "BackupManager",
        "methods": [
          "__init__",
          "_get_state_manager",
          "_get_plugin_manager",
          "_get_observability_hub",
          "_get_recovery_manager",
          "_get_boot_journal",
          "create_backup",
          "_create_snapshot",
          "_get_dir_size",
          "_compute_checksum",
          "_zip_directory",
          "list_backups",
          "delete_backup"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "json",
      "zipfile",
      "hashlib",
      "shutil",
      "datetime",
      "typing",
      "runtime.backup.models"
    ],
    "depends_on": [
      "runtime.backup.models"
    ],
    "used_by": [
      "runtime.backup.scheduler",
      "runtime.backup.__init__"
    ]
  },
  {
    "module": "runtime.backup.models",
    "cluster": "Core Runtime",
    "file_path": "runtime/backup/models.py",
    "classes": [
      {
        "name": "BackupMetadata",
        "methods": []
      },
      {
        "name": "BackupInfo",
        "methods": []
      }
    ],
    "functions": [],
    "imports": [
      "dataclasses",
      "typing",
      "datetime"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.backup.backup_manager",
      "runtime.backup.restore_manager",
      "runtime.backup.__init__"
    ]
  },
  {
    "module": "runtime.backup.restore_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/backup/restore_manager.py",
    "classes": [
      {
        "name": "RestoreManager",
        "methods": [
          "__init__",
          "restore_from_backup"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "json",
      "zipfile",
      "shutil",
      "tempfile",
      "typing",
      "runtime.backup.models"
    ],
    "depends_on": [
      "runtime.backup.models"
    ],
    "used_by": [
      "runtime.backup.__init__"
    ]
  },
  {
    "module": "runtime.backup.scheduler",
    "cluster": "Core Runtime",
    "file_path": "runtime/backup/scheduler.py",
    "classes": [
      {
        "name": "BackupScheduler",
        "methods": [
          "__init__",
          "start",
          "stop",
          "_loop",
          "_create_backup_and_rotate",
          "_rotate_backups"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "threading",
      "time",
      "typing",
      "runtime.backup.backup_manager"
    ],
    "depends_on": [
      "runtime.backup.backup_manager"
    ],
    "used_by": [
      "runtime.backup.__init__"
    ]
  },
  {
    "module": "runtime.backup.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/backup/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.backup.models",
      "runtime.backup.backup_manager",
      "runtime.backup.restore_manager",
      "runtime.backup.scheduler"
    ],
    "depends_on": [
      "runtime.backup.scheduler",
      "runtime.backup.backup_manager",
      "runtime.backup.restore_manager",
      "runtime.backup.models"
    ],
    "used_by": []
  },
  {
    "module": "runtime.cache.cache_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/cache/cache_manager.py",
    "classes": [
      {
        "name": "CacheManager",
        "methods": [
          "__init__",
          "get",
          "set",
          "invalidate",
          "clear",
          "snapshot"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "time",
      "threading"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.cache.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/cache/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.database.base",
    "cluster": "Database",
    "file_path": "runtime/database/base.py",
    "classes": [],
    "functions": [
      "_resolve_db_path",
      "get_engine",
      "get_session",
      "init_db",
      "_migrate_add_order_source",
      "_mark_existing_test_orders",
      "shutdown_db"
    ],
    "imports": [
      "os",
      "threading",
      "pathlib",
      "sqlalchemy",
      "sqlalchemy.orm"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.database.__init__",
      "runtime.database.models",
      "runtime.database.repository",
      "runtime.database.ledger"
    ]
  },
  {
    "module": "runtime.database.ledger",
    "cluster": "Database",
    "file_path": "runtime/database/ledger.py",
    "classes": [
      {
        "name": "Ledger",
        "methods": [
          "record",
          "record_order_income",
          "record_provider_payment",
          "record_commission",
          "record_refund",
          "record_profit",
          "record_deposit",
          "get_order_transactions",
          "get_order_profit",
          "get_balance_snapshot",
          "get_daily_report",
          "get_provider_spending"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "decimal",
      "typing",
      "sqlalchemy",
      "runtime.database.base",
      "runtime.database.models"
    ],
    "depends_on": [
      "runtime.database.base",
      "runtime.database.models"
    ],
    "used_by": [
      "runtime.database.__init__"
    ]
  },
  {
    "module": "runtime.database.models",
    "cluster": "Database",
    "file_path": "runtime/database/models.py",
    "classes": [
      {
        "name": "OrderStatus",
        "methods": []
      },
      {
        "name": "TransactionType",
        "methods": []
      },
      {
        "name": "ProviderStatus",
        "methods": []
      },
      {
        "name": "LotStatus",
        "methods": []
      },
      {
        "name": "User",
        "methods": [
          "__repr__"
        ]
      },
      {
        "name": "Product",
        "methods": [
          "__repr__"
        ]
      },
      {
        "name": "Lot",
        "methods": [
          "__repr__"
        ]
      },
      {
        "name": "Provider",
        "methods": [
          "__repr__"
        ]
      },
      {
        "name": "Order",
        "methods": [
          "__repr__"
        ]
      },
      {
        "name": "Transaction",
        "methods": [
          "__repr__"
        ]
      },
      {
        "name": "Review",
        "methods": [
          "__repr__"
        ]
      },
      {
        "name": "Log",
        "methods": []
      },
      {
        "name": "ProviderBalance",
        "methods": []
      },
      {
        "name": "Notification",
        "methods": []
      },
      {
        "name": "CacheEntry",
        "methods": []
      },
      {
        "name": "PluginState",
        "methods": []
      },
      {
        "name": "AnalyticsEvent",
        "methods": []
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "sqlalchemy",
      "sqlalchemy.orm",
      "runtime.database.base",
      "enum"
    ],
    "depends_on": [
      "runtime.database.base"
    ],
    "used_by": [
      "runtime.database.__init__",
      "web.seller_api",
      "runtime.database.repository",
      "runtime.database.ledger"
    ]
  },
  {
    "module": "runtime.database.repository",
    "cluster": "Database",
    "file_path": "runtime/database/repository.py",
    "classes": [
      {
        "name": "Repository",
        "methods": [
          "get_or_create_user",
          "create_order",
          "get_order",
          "get_order_by_id",
          "update_order_status",
          "get_active_orders",
          "get_orders_by_status",
          "count_orders",
          "create_lot",
          "get_lot",
          "get_lots_by_tag",
          "get_or_create_provider",
          "update_provider_balance",
          "create_review",
          "log",
          "get_dashboard_stats",
          "log_notification",
          "get_notifications",
          "get_cache",
          "set_cache",
          "cleanup_expired_cache",
          "set_plugin_state",
          "get_plugin_state",
          "record_analytics",
          "get_analytics"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "typing",
      "sqlalchemy",
      "runtime.database.base",
      "runtime.database.models"
    ],
    "depends_on": [
      "runtime.database.base",
      "runtime.database.models"
    ],
    "used_by": [
      "runtime.database.__init__"
    ]
  },
  {
    "module": "runtime.database.__init__",
    "cluster": "Database",
    "file_path": "runtime/database/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.database.base",
      "runtime.database.models",
      "runtime.database.ledger",
      "runtime.database.repository"
    ],
    "depends_on": [
      "runtime.database.base",
      "runtime.database.models",
      "runtime.database.repository",
      "runtime.database.ledger"
    ],
    "used_by": []
  },
  {
    "module": "runtime.export.export_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/export/export_manager.py",
    "classes": [
      {
        "name": "ExportManager",
        "methods": [
          "__init__",
          "create_export",
          "_get_runtime_settings",
          "_get_observability_settings",
          "_get_notifications_settings",
          "export_to_json"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "typing",
      "runtime.export.models",
      "runtime.export.schema"
    ],
    "depends_on": [
      "runtime.export.schema",
      "runtime.export.models"
    ],
    "used_by": [
      "runtime.export.__init__"
    ]
  },
  {
    "module": "runtime.export.import_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/export/import_manager.py",
    "classes": [
      {
        "name": "ImportManager",
        "methods": [
          "__init__",
          "import_from_json",
          "_calculate_changes",
          "_merge_plugins",
          "_merge_runtime_settings",
          "_merge_observability",
          "_merge_notifications",
          "_report"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "typing",
      "runtime.export.schema",
      "runtime.export.validators"
    ],
    "depends_on": [
      "runtime.export.schema",
      "runtime.export.validators"
    ],
    "used_by": [
      "runtime.export.__init__"
    ]
  },
  {
    "module": "runtime.export.models",
    "cluster": "Core Runtime",
    "file_path": "runtime/export/models.py",
    "classes": [
      {
        "name": "PluginExport",
        "methods": []
      },
      {
        "name": "RuntimeSettingsExport",
        "methods": []
      },
      {
        "name": "ObservabilityExport",
        "methods": []
      },
      {
        "name": "NotificationsExport",
        "methods": []
      },
      {
        "name": "ExportData",
        "methods": []
      }
    ],
    "functions": [],
    "imports": [
      "dataclasses",
      "typing",
      "datetime"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.export.__init__",
      "runtime.export.export_manager",
      "runtime.export.schema",
      "runtime.export.validators"
    ]
  },
  {
    "module": "runtime.export.schema",
    "cluster": "Core Runtime",
    "file_path": "runtime/export/schema.py",
    "classes": [],
    "functions": [
      "get_schema",
      "validate_export"
    ],
    "imports": [
      "json",
      "typing",
      "datetime",
      "runtime.export.models"
    ],
    "depends_on": [
      "runtime.export.models"
    ],
    "used_by": [
      "runtime.export.import_manager",
      "runtime.export.__init__",
      "runtime.export.export_manager"
    ]
  },
  {
    "module": "runtime.export.validators",
    "cluster": "Core Runtime",
    "file_path": "runtime/export/validators.py",
    "classes": [],
    "functions": [
      "validate_plugins",
      "validate_runtime_settings",
      "validate_observability",
      "validate_notifications"
    ],
    "imports": [
      "typing",
      "runtime.export.models"
    ],
    "depends_on": [
      "runtime.export.models"
    ],
    "used_by": [
      "runtime.export.import_manager",
      "runtime.export.__init__"
    ]
  },
  {
    "module": "runtime.export.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/export/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.export.models",
      "runtime.export.export_manager",
      "runtime.export.import_manager",
      "runtime.export.schema",
      "runtime.export.validators"
    ],
    "depends_on": [
      "runtime.export.import_manager",
      "runtime.export.export_manager",
      "runtime.export.validators",
      "runtime.export.models",
      "runtime.export.schema"
    ],
    "used_by": []
  },
  {
    "module": "runtime.messages.delivery_messages",
    "cluster": "CCE",
    "file_path": "runtime/messages/delivery_messages.py",
    "classes": [
      {
        "name": "DeliveryMessages",
        "methods": [
          "__init__",
          "send_digital_account",
          "send_link"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "typing",
      "message_manager"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.messages.error_messages",
    "cluster": "CCE",
    "file_path": "runtime/messages/error_messages.py",
    "classes": [
      {
        "name": "ErrorMessages",
        "methods": [
          "__init__",
          "supplier_balance_zero",
          "supplier_error",
          "site_unavailable",
          "api_unavailable",
          "limit_exceeded",
          "out_of_stock"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "typing",
      "message_manager"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow",
      "runtime.order_tracker"
    ]
  },
  {
    "module": "runtime.messages.formatter",
    "cluster": "CCE",
    "file_path": "runtime/messages/formatter.py",
    "classes": [
      {
        "name": "MessageFormatter",
        "methods": [
          "__init__",
          "format",
          "_enrich_context",
          "_load_order_from_db",
          "_resolve_eta_from_order",
          "_clean",
          "build_order_title",
          "build_eta_text",
          "build_delivery_data"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "re",
      "typing",
      "templates"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.messages.message_manager",
    "cluster": "CCE",
    "file_path": "runtime/messages/message_manager.py",
    "classes": [
      {
        "name": "MessageManager",
        "methods": [
          "__init__",
          "set_sender",
          "set_admin_chat_id",
          "_now",
          "_mark_sent",
          "_is_sent",
          "send",
          "send_admin",
          "get_order_stage",
          "set_order_stage",
          "clear_sent",
          "mark_sent",
          "formatter"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "threading",
      "time",
      "logging",
      "typing",
      "formatter",
      "templates"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow",
      "runtime.order_tracker"
    ]
  },
  {
    "module": "runtime.messages.notification_messages",
    "cluster": "CCE",
    "file_path": "runtime/messages/notification_messages.py",
    "classes": [
      {
        "name": "NotificationMessages",
        "methods": [
          "__init__",
          "admin_new_order",
          "admin_supplier_down",
          "admin_refund",
          "admin_plugin_error",
          "admin_funpay_unavailable",
          "admin_order_timeout"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "typing",
      "message_manager"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow",
      "runtime.order_tracker"
    ]
  },
  {
    "module": "runtime.messages.order_messages",
    "cluster": "CCE",
    "file_path": "runtime/messages/order_messages.py",
    "classes": [
      {
        "name": "OrderMessages",
        "methods": [
          "__init__",
          "on_new_order",
          "on_greeting",
          "on_link_request",
          "on_link_received",
          "on_confirm_request",
          "on_confirm",
          "on_sent_to_supplier",
          "on_processing",
          "on_completed",
          "on_completed_reminder",
          "on_thanks",
          "on_review_prompt",
          "on_cancelled",
          "on_refund",
          "_resolve_eta"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "typing",
      "message_manager",
      "formatter",
      "stage_detector"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow",
      "runtime.order_tracker"
    ]
  },
  {
    "module": "runtime.messages.recovery_messages",
    "cluster": "CCE",
    "file_path": "runtime/messages/recovery_messages.py",
    "classes": [
      {
        "name": "RecoveryMessages",
        "methods": [
          "__init__",
          "supplier_error",
          "balance_zero",
          "site_unavailable",
          "api_unavailable",
          "out_of_stock"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "typing",
      "message_manager"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow"
    ]
  },
  {
    "module": "runtime.messages.review_messages",
    "cluster": "CCE",
    "file_path": "runtime/messages/review_messages.py",
    "classes": [
      {
        "name": "ReviewMessages",
        "methods": [
          "__init__",
          "on_positive_review",
          "on_negative_review",
          "on_neutral_review"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "typing",
      "message_manager"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow"
    ]
  },
  {
    "module": "runtime.messages.scenario",
    "cluster": "CCE",
    "file_path": "runtime/messages/scenario.py",
    "classes": [
      {
        "name": "ConversationScenario",
        "methods": [
          "__init__",
          "should_run",
          "build_context"
        ]
      },
      {
        "name": "ScenarioEngine",
        "methods": [
          "__init__",
          "_register_scenarios",
          "get_stage",
          "execute_for_stage",
          "execute_delivery",
          "execute_review_response",
          "execute_error",
          "execute_recovery",
          "execute_notification",
          "get_stage_name"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "logging",
      "typing",
      "message_manager",
      "order_messages",
      "delivery_messages",
      "error_messages",
      "review_messages",
      "notification_messages",
      "recovery_messages",
      "stage_detector"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.order_flow"
    ]
  },
  {
    "module": "runtime.messages.stage_detector",
    "cluster": "CCE",
    "file_path": "runtime/messages/stage_detector.py",
    "classes": [
      {
        "name": "OrderStageDetector",
        "methods": [
          "__init__",
          "detect",
          "get_stage_name",
          "_get_api_status"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "logging",
      "time",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.messages.templates",
    "cluster": "CCE",
    "file_path": "runtime/messages/templates.py",
    "classes": [
      {
        "name": "MessageTemplate",
        "methods": []
      }
    ],
    "functions": [
      "get_template"
    ],
    "imports": [
      "__future__",
      "dataclasses",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.messages.__init__",
    "cluster": "CCE",
    "file_path": "runtime/messages/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "message_manager",
      "stage_detector",
      "scenario",
      "formatter",
      "templates",
      "order_messages",
      "delivery_messages",
      "error_messages",
      "review_messages",
      "notification_messages",
      "recovery_messages"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.migrations.backup_migrations",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/backup_migrations.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.migrations.base",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/base.py",
    "classes": [
      {
        "name": "BaseMigration",
        "methods": [
          "from_version",
          "to_version",
          "apply"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "abc",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.migrations.versions.v1_to_v2_example",
      "runtime.migrations.registry"
    ]
  },
  {
    "module": "runtime.migrations.export_migrations",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/export_migrations.py",
    "classes": [],
    "functions": [],
    "imports": [
      "typing",
      "runtime.migrations.migration_base",
      "runtime.migrations.migration_registry"
    ],
    "depends_on": [
      "runtime.migrations.migration_base",
      "runtime.migrations.migration_registry"
    ],
    "used_by": []
  },
  {
    "module": "runtime.migrations.migration_base",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/migration_base.py",
    "classes": [
      {
        "name": "BaseMigration",
        "methods": [
          "apply",
          "from_version",
          "to_version"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "abc",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.migrations.__init__",
      "runtime.migrations.migration_registry",
      "runtime.migrations.export_migrations"
    ]
  },
  {
    "module": "runtime.migrations.migration_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/migration_manager.py",
    "classes": [
      {
        "name": "MigrationPathNotFoundError",
        "methods": []
      },
      {
        "name": "MigrationManager",
        "methods": [
          "__init__",
          "_migrate_chain",
          "migrate_export",
          "migrate_snapshot",
          "migrate_backup",
          "get_current_versions"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "typing",
      "runtime.migrations.migration_registry"
    ],
    "depends_on": [
      "runtime.migrations.migration_registry"
    ],
    "used_by": [
      "runtime.migrations.__init__"
    ]
  },
  {
    "module": "runtime.migrations.migration_registry",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/migration_registry.py",
    "classes": [
      {
        "name": "MigrationRegistry",
        "methods": [
          "__init__",
          "register_export",
          "register_snapshot",
          "register_backup",
          "get_export_migration",
          "get_snapshot_migration",
          "get_backup_migration",
          "get_export_versions",
          "get_snapshot_versions",
          "get_backup_versions"
        ]
      }
    ],
    "functions": [
      "get_registry"
    ],
    "imports": [
      "typing",
      "runtime.migrations.migration_base"
    ],
    "depends_on": [
      "runtime.migrations.migration_base"
    ],
    "used_by": [
      "runtime.migrations.__init__",
      "runtime.migrations.migration_manager",
      "runtime.migrations.export_migrations"
    ]
  },
  {
    "module": "runtime.migrations.registry",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/registry.py",
    "classes": [
      {
        "name": "MigrationRegistry",
        "methods": [
          "__init__",
          "register_export",
          "register_snapshot",
          "register_backup",
          "get_export_migration",
          "get_snapshot_migration",
          "get_backup_migration",
          "get_export_versions",
          "get_snapshot_versions",
          "get_backup_versions"
        ]
      }
    ],
    "functions": [
      "get_registry"
    ],
    "imports": [
      "typing",
      "runtime.migrations.base"
    ],
    "depends_on": [
      "runtime.migrations.base"
    ],
    "used_by": [
      "runtime.migrations.versions.v1_to_v2_example"
    ]
  },
  {
    "module": "runtime.migrations.snapshot_migrations",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/snapshot_migrations.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.migrations.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.migrations.migration_manager",
      "runtime.migrations.migration_registry",
      "runtime.migrations.migration_base"
    ],
    "depends_on": [
      "runtime.migrations.migration_base",
      "runtime.migrations.migration_manager",
      "runtime.migrations.migration_registry"
    ],
    "used_by": []
  },
  {
    "module": "runtime.migrations.versions.v1_to_v2_example",
    "cluster": "Core Runtime",
    "file_path": "runtime/migrations/versions/v1_to_v2_example.py",
    "classes": [
      {
        "name": "ExportV1ToV2",
        "methods": [
          "apply"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "typing",
      "runtime.migrations.base",
      "runtime.migrations.registry"
    ],
    "depends_on": [
      "runtime.migrations.base",
      "runtime.migrations.registry"
    ],
    "used_by": []
  },
  {
    "module": "runtime.notifications.notification_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/notification_manager.py",
    "classes": [
      {
        "name": "NotificationManager",
        "methods": [
          "__init__",
          "register_channel",
          "subscribe_to_event_bus",
          "_on_event",
          "_on_health_update",
          "send",
          "get_history",
          "clear_history"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "runtime.notifications.notification_types",
      "runtime.notifications.notification_queue",
      "runtime.notifications.rate_limiter",
      "runtime.notifications.notification_rules"
    ],
    "depends_on": [
      "runtime.notifications.notification_queue",
      "runtime.notifications.notification_types",
      "runtime.notifications.rate_limiter",
      "runtime.notifications.notification_rules"
    ],
    "used_by": [
      "web.alerts_api",
      "runtime.notifications.__init__"
    ]
  },
  {
    "module": "runtime.notifications.notification_queue",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/notification_queue.py",
    "classes": [
      {
        "name": "NotificationQueue",
        "methods": [
          "__init__",
          "add",
          "get_all",
          "get_last",
          "clear",
          "count"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "collections",
      "threading",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.notifications.notification_manager"
    ]
  },
  {
    "module": "runtime.notifications.notification_rules",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/notification_rules.py",
    "classes": [
      {
        "name": "NotificationRules",
        "methods": [
          "__init__",
          "evaluate_event",
          "evaluate_health"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "runtime.notifications.notification_types",
      "time"
    ],
    "depends_on": [
      "runtime.notifications.notification_types"
    ],
    "used_by": [
      "runtime.notifications.notification_manager"
    ]
  },
  {
    "module": "runtime.notifications.notification_types",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/notification_types.py",
    "classes": [
      {
        "name": "NotificationType",
        "methods": []
      },
      {
        "name": "Notification",
        "methods": [
          "to_dict"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "enum",
      "dataclasses",
      "time",
      "uuid"
    ],
    "depends_on": [],
    "used_by": [
      "web.alerts_api",
      "runtime.notifications.channels.log_channel",
      "runtime.notifications.notification_rules",
      "runtime.notifications.channels.discord_channel",
      "runtime.notifications.notification_manager",
      "runtime.notifications.channels.base_channel",
      "runtime.notifications.channels.dashboard_channel",
      "runtime.notifications.__init__"
    ]
  },
  {
    "module": "runtime.notifications.rate_limiter",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/rate_limiter.py",
    "classes": [
      {
        "name": "RateLimiter",
        "methods": [
          "__init__",
          "allow"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "collections",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.notifications.notification_manager"
    ]
  },
  {
    "module": "runtime.notifications.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.notifications.notification_manager",
      "runtime.notifications.notification_types",
      "runtime.notifications.channels.log_channel",
      "runtime.notifications.channels.dashboard_channel",
      "runtime.notifications.channels.discord_channel"
    ],
    "depends_on": [
      "runtime.notifications.channels.discord_channel",
      "runtime.notifications.notification_types",
      "runtime.notifications.channels.log_channel",
      "runtime.notifications.channels.dashboard_channel",
      "runtime.notifications.notification_manager"
    ],
    "used_by": []
  },
  {
    "module": "runtime.notifications.channels.base_channel",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/channels/base_channel.py",
    "classes": [
      {
        "name": "BaseChannel",
        "methods": [
          "send"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "runtime.notifications.notification_types"
    ],
    "depends_on": [
      "runtime.notifications.notification_types"
    ],
    "used_by": [
      "runtime.notifications.channels.discord_channel",
      "runtime.notifications.channels.dashboard_channel",
      "runtime.notifications.channels.log_channel"
    ]
  },
  {
    "module": "runtime.notifications.channels.dashboard_channel",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/channels/dashboard_channel.py",
    "classes": [
      {
        "name": "DashboardChannel",
        "methods": [
          "__init__",
          "send"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "runtime.notifications.channels.base_channel",
      "runtime.notifications.notification_types"
    ],
    "depends_on": [
      "runtime.notifications.channels.base_channel",
      "runtime.notifications.notification_types"
    ],
    "used_by": [
      "runtime.notifications.__init__"
    ]
  },
  {
    "module": "runtime.notifications.channels.discord_channel",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/channels/discord_channel.py",
    "classes": [
      {
        "name": "DiscordChannel",
        "methods": [
          "__init__",
          "send"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "datetime",
      "runtime.http_client",
      "runtime.notifications.channels.base_channel",
      "runtime.notifications.notification_types"
    ],
    "depends_on": [
      "runtime.notifications.channels.base_channel",
      "runtime.http_client",
      "runtime.notifications.notification_types"
    ],
    "used_by": [
      "runtime.notifications.__init__"
    ]
  },
  {
    "module": "runtime.notifications.channels.log_channel",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/channels/log_channel.py",
    "classes": [
      {
        "name": "LogChannel",
        "methods": [
          "__init__",
          "send"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "runtime.notifications.channels.base_channel",
      "runtime.notifications.notification_types"
    ],
    "depends_on": [
      "runtime.notifications.channels.base_channel",
      "runtime.notifications.notification_types"
    ],
    "used_by": [
      "runtime.notifications.__init__"
    ]
  },
  {
    "module": "runtime.notifications.channels.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/notifications/channels/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.observability.event_store",
    "cluster": "Core Runtime",
    "file_path": "runtime/observability/event_store.py",
    "classes": [
      {
        "name": "EventStore",
        "methods": [
          "__init__",
          "add",
          "get_all",
          "get_by_correlation",
          "get_by_plugin",
          "get_by_severity",
          "get_errors",
          "clear",
          "size",
          "get_stats"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "collections",
      "typing",
      "runtime.event_types"
    ],
    "depends_on": [
      "runtime.event_types"
    ],
    "used_by": [
      "runtime.__init__",
      "runtime.observability.health_engine",
      "runtime.observability.observability_hub"
    ]
  },
  {
    "module": "runtime.observability.health_engine",
    "cluster": "Core Runtime",
    "file_path": "runtime/observability/health_engine.py",
    "classes": [
      {
        "name": "HealthEngineV2",
        "methods": [
          "__init__",
          "calculate_score",
          "get_status",
          "get_detailed_health"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "runtime.observability.metrics",
      "runtime.observability.event_store"
    ],
    "depends_on": [
      "runtime.observability.event_store",
      "runtime.observability.metrics"
    ],
    "used_by": [
      "runtime.__init__",
      "runtime.observability.observability_hub"
    ]
  },
  {
    "module": "runtime.observability.metrics",
    "cluster": "Core Runtime",
    "file_path": "runtime/observability/metrics.py",
    "classes": [
      {
        "name": "PluginMetrics",
        "methods": [
          "__init__",
          "record_event",
          "record_state_change",
          "record_restart",
          "set_uptime_start",
          "get_uptime",
          "get_stability_score",
          "to_dict"
        ]
      },
      {
        "name": "MetricsCollector",
        "methods": [
          "__init__",
          "get_or_create",
          "record_event",
          "record_state_change",
          "record_restart",
          "set_uptime_start",
          "get_all_metrics",
          "get_plugin_metrics",
          "get_summary"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "collections",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.__init__",
      "runtime.observability.health_engine",
      "runtime.observability.observability_hub"
    ]
  },
  {
    "module": "runtime.observability.observability_hub",
    "cluster": "Core Runtime",
    "file_path": "runtime/observability/observability_hub.py",
    "classes": [
      {
        "name": "ObservabilityHub",
        "methods": [
          "__init__",
          "_on_event",
          "_publish_metrics",
          "_publish_health",
          "record_plugin_state_change",
          "record_plugin_restart",
          "record_plugin_uptime_start",
          "get_health_score",
          "get_health_status",
          "get_detailed_health",
          "get_plugin_metrics",
          "get_event_history",
          "get_events_by_correlation",
          "get_stats"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "eventbus",
      "runtime.event_types",
      "runtime.observability.event_store",
      "runtime.observability.metrics",
      "runtime.observability.health_engine"
    ],
    "depends_on": [
      "runtime.event_types",
      "runtime.observability.metrics",
      "runtime.observability.event_store",
      "runtime.observability.health_engine"
    ],
    "used_by": [
      "runtime.__init__"
    ]
  },
  {
    "module": "runtime.observability.resource_monitor",
    "cluster": "Core Runtime",
    "file_path": "runtime/observability/resource_monitor.py",
    "classes": [
      {
        "name": "ResourceMonitor",
        "methods": [
          "__init__",
          "start",
          "stop",
          "_monitor_loop",
          "_collect_resources"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "psutil",
      "threading",
      "time",
      "typing"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "runtime.recovery.boot_journal",
    "cluster": "Core Runtime",
    "file_path": "runtime/recovery/boot_journal.py",
    "classes": [
      {
        "name": "BootJournal",
        "methods": [
          "__init__",
          "_ensure_dir",
          "load",
          "save",
          "mark_start",
          "mark_shutdown",
          "was_crash",
          "get_last_start",
          "get_last_shutdown"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "os",
      "time",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.recovery.__init__",
      "runtime.recovery.recovery_manager"
    ]
  },
  {
    "module": "runtime.recovery.recovery_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/recovery/recovery_manager.py",
    "classes": [
      {
        "name": "RecoveryManager",
        "methods": [
          "__init__",
          "is_crash_recovery",
          "perform_recovery",
          "get_recovery_status"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "typing",
      "runtime.recovery.boot_journal",
      "runtime.recovery.report",
      "runtime.state.storage",
      "runtime.state.migrations",
      "runtime.state.snapshot_engine"
    ],
    "depends_on": [
      "runtime.state.migrations",
      "runtime.recovery.boot_journal",
      "runtime.recovery.report",
      "runtime.state.snapshot_engine",
      "runtime.state.storage"
    ],
    "used_by": [
      "runtime.recovery.__init__"
    ]
  },
  {
    "module": "runtime.recovery.report",
    "cluster": "Core Runtime",
    "file_path": "runtime/recovery/report.py",
    "classes": [
      {
        "name": "RecoveryReport",
        "methods": [
          "__init__",
          "set_crash",
          "set_snapshot",
          "add_restored",
          "add_skipped",
          "set_message",
          "to_dict",
          "save"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.recovery.__init__",
      "runtime.recovery.recovery_manager"
    ]
  },
  {
    "module": "runtime.recovery.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/recovery/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.recovery.boot_journal",
      "runtime.recovery.recovery_manager",
      "runtime.recovery.report"
    ],
    "depends_on": [
      "runtime.recovery.report",
      "runtime.recovery.recovery_manager",
      "runtime.recovery.boot_journal"
    ],
    "used_by": []
  },
  {
    "module": "runtime.state.migrations",
    "cluster": "Core Runtime",
    "file_path": "runtime/state/migrations.py",
    "classes": [],
    "functions": [
      "migrate_snapshot"
    ],
    "imports": [
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.state.state_manager",
      "runtime.recovery.recovery_manager",
      "runtime.state.__init__"
    ]
  },
  {
    "module": "runtime.state.snapshot_engine",
    "cluster": "Core Runtime",
    "file_path": "runtime/state/snapshot_engine.py",
    "classes": [
      {
        "name": "SnapshotEngine",
        "methods": [
          "__init__",
          "create_snapshot",
          "apply_snapshot",
          "_validate_snapshot"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.state.state_manager",
      "runtime.recovery.recovery_manager",
      "runtime.state.__init__"
    ]
  },
  {
    "module": "runtime.state.state_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/state/state_manager.py",
    "classes": [
      {
        "name": "StateManager",
        "methods": [
          "__init__",
          "save_snapshot",
          "load_snapshot",
          "_autosave_loop",
          "start_autosave",
          "stop_autosave"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "threading",
      "time",
      "typing",
      "runtime.state.storage",
      "runtime.state.snapshot_engine",
      "runtime.state.migrations"
    ],
    "depends_on": [
      "runtime.state.migrations",
      "runtime.state.snapshot_engine",
      "runtime.state.storage"
    ],
    "used_by": [
      "runtime.state.__init__"
    ]
  },
  {
    "module": "runtime.state.storage",
    "cluster": "Core Runtime",
    "file_path": "runtime/state/storage.py",
    "classes": [
      {
        "name": "JsonStorage",
        "methods": [
          "__init__",
          "_ensure_dir",
          "save",
          "load",
          "clear"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "json",
      "tempfile",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.state.state_manager",
      "runtime.recovery.recovery_manager",
      "runtime.state.__init__"
    ]
  },
  {
    "module": "runtime.state.__init__",
    "cluster": "Core Runtime",
    "file_path": "runtime/state/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "runtime.state.state_manager",
      "runtime.state.snapshot_engine",
      "runtime.state.storage",
      "runtime.state.migrations"
    ],
    "depends_on": [
      "runtime.state.state_manager",
      "runtime.state.migrations",
      "runtime.state.snapshot_engine",
      "runtime.state.storage"
    ],
    "used_by": []
  },
  {
    "module": "runtime.websocket.connection_manager",
    "cluster": "Core Runtime",
    "file_path": "runtime/websocket/connection_manager.py",
    "classes": [
      {
        "name": "ConnectionManager",
        "methods": [
          "__init__",
          "register",
          "unregister",
          "broadcast",
          "get_clients_count",
          "get_message_count"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "threading",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "runtime.websocket.websocket_hub"
    ]
  },
  {
    "module": "runtime.websocket.event_serializer",
    "cluster": "Core Runtime",
    "file_path": "runtime/websocket/event_serializer.py",
    "classes": [],
    "functions": [
      "serialize_event"
    ],
    "imports": [
      "json",
      "runtime.event_types"
    ],
    "depends_on": [
      "runtime.event_types"
    ],
    "used_by": [
      "runtime.websocket.websocket_hub"
    ]
  },
  {
    "module": "runtime.websocket.websocket_hub",
    "cluster": "Core Runtime",
    "file_path": "runtime/websocket/websocket_hub.py",
    "classes": [
      {
        "name": "WebSocketHub",
        "methods": [
          "__init__",
          "broadcast_notification",
          "_on_event",
          "_on_health_update",
          "_on_metrics_update",
          "get_stats",
          "stop"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "json",
      "runtime.websocket.connection_manager",
      "runtime.websocket.event_serializer",
      "runtime.event_types"
    ],
    "depends_on": [
      "runtime.event_types",
      "runtime.websocket.event_serializer",
      "runtime.websocket.connection_manager"
    ],
    "used_by": [
      "runtime.__init__"
    ]
  },
  {
    "module": "plugins.autobump_plugin",
    "cluster": "Plugins",
    "file_path": "plugins/autobump_plugin.py",
    "classes": [
      {
        "name": "AutoBumpPlugin",
        "methods": [
          "__init__",
          "on_load",
          "on_enable",
          "on_disable",
          "on_unload",
          "on_error",
          "_loop",
          "_run_once",
          "_get_target_categories",
          "_bump_category",
          "_log",
          "action_test_bump",
          "action_reset_stats",
          "get_logs",
          "get_stats"
        ]
      }
    ],
    "functions": [
      "get_plugin_stats"
    ],
    "imports": [
      "time",
      "threading",
      "json",
      "datetime",
      "collections",
      "pathlib",
      "plugins.plugin_base",
      "runtime.http_client"
    ],
    "depends_on": [
      "plugins.plugin_base",
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "plugins.autodonate_plugin",
    "cluster": "Plugins",
    "file_path": "plugins/autodonate_plugin.py",
    "classes": [
      {
        "name": "AutoDonatePlugin",
        "methods": [
          "__init__",
          "on_enable",
          "on_disable",
          "on_unload",
          "on_load",
          "on_event",
          "_on_new_order",
          "_on_new_message",
          "_on_order_completed",
          "_on_review_received",
          "_detect_supplier",
          "_get_supplier_config",
          "_parse_kosell_hours",
          "_create_supplier_order",
          "_create_gorgonaboosts_order",
          "_create_holdboost_order",
          "_create_shopclaude_order",
          "_create_kosell_order",
          "_extract_invite_from_title",
          "_extract_quantity_from_title",
          "_parse_kosell_product",
          "_send_credentials",
          "_deactivate_supplier_lots",
          "check_balance",
          "_is_balance_sufficient",
          "check_stock",
          "_send_message",
          "_log",
          "_get_data_dir",
          "_start_replenish_timer",
          "_stop_replenish_timer",
          "_replenish_loop",
          "_check_pending_orders",
          "_send_telegram_notification",
          "_add_pending_order",
          "action_test_connection",
          "action_check_stock"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "re",
      "threading",
      "pathlib",
      "plugins.plugin_base",
      "runtime.http_client",
      "runtime.order_tracker"
    ],
    "depends_on": [
      "runtime.order_tracker",
      "plugins.plugin_base",
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "plugins.autosmm_plugin",
    "cluster": "Plugins",
    "file_path": "plugins/autosmm_plugin.py",
    "classes": [
      {
        "name": "AutoSMMPlugin",
        "methods": [
          "__init__",
          "_get_chat_lock",
          "on_load",
          "on_enable",
          "on_disable",
          "on_unload",
          "on_error",
          "_loop",
          "_check_active_orders",
          "_on_order_completed",
          "_on_order_partial",
          "_on_order_failed",
          "_check_balance",
          "on_event",
          "_on_new_order",
          "_on_new_message",
          "_handle_link",
          "_handle_confirm",
          "_create_twiboost_order",
          "_check_looksmm_price",
          "_create_looksmm_order",
          "_create_order_with_fallback",
          "_check_twiboost_price",
          "_on_order_completed",
          "_on_review_received",
          "_notify_telegram",
          "_b40_resolve_service_info",
          "_b40_parse_quantity_from_title",
          "_send_message",
          "_refund_order",
          "_is_allowed_domain",
          "_looks_like_url",
          "_get_data_dir",
          "_load_active_orders",
          "_save_active_orders",
          "_now_str",
          "_log",
          "action_check_balance",
          "action_test_api",
          "action_load_services",
          "_services_cache_file",
          "_save_services_cache",
          "_load_services_cache",
          "_fetch_twiboost_services",
          "_fetch_my_lots",
          "_detect_profile_for_lot",
          "action_load_twiboost_services",
          "action_scan_my_lots",
          "action_apply_auto_match",
          "action_confirm_suggested",
          "action_remove_mapping",
          "action_get_current_mappings",
          "_check_balance_and_deactivate",
          "_deactivate_as_lots",
          "action_generate_lots_from_niches",
          "get_logs",
          "get_stats"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "time",
      "threading",
      "json",
      "re",
      "collections",
      "pathlib",
      "urllib.parse",
      "plugins.plugin_base",
      "runtime.http_client",
      "runtime.order_tracker"
    ],
    "depends_on": [
      "runtime.order_tracker",
      "plugins.plugin_base",
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "plugins.config_manager",
    "cluster": "Plugins",
    "file_path": "plugins/config_manager.py",
    "classes": [],
    "functions": [
      "get_config_path",
      "load_raw_config",
      "create_default_config",
      "load_plugin_config",
      "save_plugin_config"
    ],
    "imports": [
      "os",
      "json",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.plugin_base"
    ]
  },
  {
    "module": "plugins.dependency_manager",
    "cluster": "Plugins",
    "file_path": "plugins/dependency_manager.py",
    "classes": [
      {
        "name": "DependencyError",
        "methods": []
      },
      {
        "name": "CircularDependencyError",
        "methods": []
      },
      {
        "name": "MissingDependencyError",
        "methods": []
      },
      {
        "name": "DependencyGraph",
        "methods": [
          "__init__",
          "add_plugin",
          "remove_plugin",
          "validate_dependencies",
          "detect_circular",
          "topological_sort",
          "get_hard_dependents",
          "get_soft_dependents",
          "get_dependents",
          "can_disable",
          "get_plugin_info"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "typing",
      "collections"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.plugin_manager"
    ]
  },
  {
    "module": "plugins.health_score",
    "cluster": "Plugins",
    "file_path": "plugins/health_score.py",
    "classes": [
      {
        "name": "PluginHealthScore",
        "methods": [
          "__init__",
          "update_latency",
          "update_error",
          "update_restart",
          "update_event_count",
          "tick",
          "calculate_score"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "collections",
      "typing"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.plugin_manager"
    ]
  },
  {
    "module": "plugins.loader",
    "cluster": "Plugins",
    "file_path": "plugins/loader.py",
    "classes": [],
    "functions": [
      "discover_plugins",
      "load_plugin",
      "load_plugins",
      "reload_plugin_config"
    ],
    "imports": [
      "os",
      "sys",
      "importlib",
      "inspect",
      "typing",
      "plugins.plugin_base"
    ],
    "depends_on": [
      "plugins.plugin_base"
    ],
    "used_by": []
  },
  {
    "module": "plugins.logger_plugin",
    "cluster": "Plugins",
    "file_path": "plugins/logger_plugin.py",
    "classes": [
      {
        "name": "LoggerPlugin",
        "methods": [
          "on_init",
          "on_load",
          "on_enable",
          "on_disable",
          "on_error",
          "on_unload",
          "on_event"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "plugins.plugin_base"
    ],
    "depends_on": [
      "plugins.plugin_base"
    ],
    "used_by": []
  },
  {
    "module": "plugins.plugin_base",
    "cluster": "Plugins",
    "file_path": "plugins/plugin_base.py",
    "classes": [
      {
        "name": "PluginBase",
        "methods": [
          "__init__",
          "set_message_manager",
          "get_info",
          "get_dependencies",
          "get_optional_dependencies",
          "on_load",
          "on_enable",
          "on_disable",
          "on_event",
          "on_error",
          "on_unload",
          "is_enabled",
          "is_loaded",
          "_set_enabled",
          "_set_loaded",
          "get_config",
          "load_config",
          "save_config",
          "reload_config",
          "get_config_value",
          "set_config_value",
          "get_secret",
          "set_secret",
          "get_full_info"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "typing",
      "plugins.config_manager",
      "security.secrets_manager"
    ],
    "depends_on": [
      "plugins.config_manager",
      "security.secrets_manager"
    ],
    "used_by": [
      "plugins.loader",
      "plugins.telegram_notifier_plugin",
      "plugins.plugin_manager",
      "plugins.autobump_plugin",
      "plugins.autodonate_plugin",
      "plugins.logger_plugin",
      "plugins.stars_plugin",
      "plugins.autosmm_plugin"
    ]
  },
  {
    "module": "plugins.plugin_manager",
    "cluster": "Plugins",
    "file_path": "plugins/plugin_manager.py",
    "classes": [
      {
        "name": "PluginManager",
        "methods": [
          "__init__",
          "set_event_bus",
          "_get_fsm",
          "_transition",
          "register",
          "finalize_registration",
          "_start_watchdog",
          "_watchdog_loop",
          "_check_plugin_health",
          "quarantine_plugin",
          "release_quarantine",
          "is_quarantined",
          "get_plugin_health_score",
          "get_all_health_scores",
          "get_quarantine_data",
          "restore_quarantine",
          "get_load_order",
          "can_disable",
          "get_dependents",
          "unregister",
          "enable",
          "disable",
          "emit",
          "get_plugin_state",
          "get_all_states",
          "get_plugins",
          "get_plugins_info",
          "reload_plugin_config",
          "get_plugins_count",
          "get_plugin_object",
          "get_plugin_names",
          "plugin_exists",
          "restore_states"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "threading",
      "time",
      "typing",
      "collections",
      "plugins.plugin_base",
      "plugins.plugin_state",
      "plugins.plugin_registry",
      "plugins.dependency_manager",
      "plugins.health_score",
      "plugins.execution"
    ],
    "depends_on": [
      "plugins.dependency_manager",
      "plugins.plugin_state",
      "plugins.health_score",
      "plugins.plugin_base",
      "plugins.plugin_registry",
      "plugins.execution"
    ],
    "used_by": [
      "runtime.runtime_controller"
    ]
  },
  {
    "module": "plugins.plugin_registry",
    "cluster": "Plugins",
    "file_path": "plugins/plugin_registry.py",
    "classes": [
      {
        "name": "PluginRegistry",
        "methods": [
          "__init__",
          "register_metadata",
          "update_state",
          "get_plugin",
          "get_all_plugins",
          "get_plugins_count",
          "get_plugin_state",
          "plugin_exists"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "typing",
      "plugins.plugin_state"
    ],
    "depends_on": [
      "plugins.plugin_state"
    ],
    "used_by": [
      "plugins.plugin_manager"
    ]
  },
  {
    "module": "plugins.plugin_state",
    "cluster": "Plugins",
    "file_path": "plugins/plugin_state.py",
    "classes": [
      {
        "name": "PluginState",
        "methods": []
      },
      {
        "name": "PluginErrorContext",
        "methods": [
          "to_string"
        ]
      },
      {
        "name": "PluginStateMachine",
        "methods": [
          "__init__",
          "get_state",
          "get_state_name",
          "get_error_context",
          "get_error_message",
          "can_transition",
          "apply_transition"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "enum",
      "typing",
      "dataclasses"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.plugin_registry",
      "plugins.plugin_manager"
    ]
  },
  {
    "module": "plugins.stars_plugin",
    "cluster": "Plugins",
    "file_path": "plugins/stars_plugin.py",
    "classes": [
      {
        "name": "StarsPlugin",
        "methods": [
          "__init__",
          "on_load",
          "on_event",
          "_on_new_stars_order",
          "_create_stars_order",
          "_check_stars_status",
          "_parse_stars",
          "_get_buyer_username",
          "_send_message",
          "_register_order_in_tracker",
          "_log",
          "_get_data_dir",
          "action_test_connection"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "os",
      "re",
      "time",
      "json",
      "pathlib",
      "typing",
      "plugins.plugin_base",
      "runtime.http_client",
      "runtime.order_tracker"
    ],
    "depends_on": [
      "runtime.order_tracker",
      "plugins.plugin_base",
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "plugins.telegram_notifier_plugin",
    "cluster": "Plugins",
    "file_path": "plugins/telegram_notifier_plugin.py",
    "classes": [
      {
        "name": "TelegramNotifierPlugin",
        "methods": [
          "__init__",
          "on_load",
          "on_enable",
          "on_disable",
          "on_unload",
          "on_event",
          "_send_telegram",
          "_answer_callback",
          "_edit_message",
          "_start_polling",
          "_stop_polling",
          "_polling_loop",
          "_handle_update",
          "_handle_callback",
          "_handle_generate_lots",
          "_handle_deactivate_lots",
          "_handle_toggle_auto_lots",
          "_handle_simulate",
          "_send_main_menu",
          "_api_get",
          "_build_market_report",
          "_build_balance_report",
          "_build_sales_report",
          "_build_health_report",
          "_log",
          "action_test"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "threading",
      "json",
      "os",
      "datetime",
      "typing",
      "plugins.plugin_base",
      "runtime.http_client"
    ],
    "depends_on": [
      "plugins.plugin_base",
      "runtime.http_client"
    ],
    "used_by": []
  },
  {
    "module": "plugins.execution.base",
    "cluster": "Plugins",
    "file_path": "plugins/execution/base.py",
    "classes": [
      {
        "name": "PluginExecutor",
        "methods": [
          "execute_event",
          "start",
          "stop"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "abc"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.execution.subprocess_executor",
      "plugins.execution.inprocess_executor",
      "plugins.plugin_manager",
      "plugins.execution.__init__",
      "plugins.execution.executor_registry"
    ]
  },
  {
    "module": "plugins.execution.executor_registry",
    "cluster": "Plugins",
    "file_path": "plugins/execution/executor_registry.py",
    "classes": [
      {
        "name": "ExecutorRegistry",
        "methods": [
          "__init__",
          "register",
          "get",
          "get_default"
        ]
      }
    ],
    "functions": [
      "get_executor_registry"
    ],
    "imports": [
      "typing",
      "plugins.execution.base",
      "plugins.execution.inprocess_executor",
      "plugins.execution.subprocess_executor"
    ],
    "depends_on": [
      "plugins.execution.subprocess_executor",
      "plugins.execution.inprocess_executor",
      "plugins.execution.base"
    ],
    "used_by": [
      "plugins.plugin_manager",
      "plugins.execution.__init__"
    ]
  },
  {
    "module": "plugins.execution.inprocess_executor",
    "cluster": "Plugins",
    "file_path": "plugins/execution/inprocess_executor.py",
    "classes": [
      {
        "name": "InProcessExecutor",
        "methods": [
          "execute_event",
          "start",
          "stop"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "plugins.execution.base"
    ],
    "depends_on": [
      "plugins.execution.base"
    ],
    "used_by": [
      "plugins.plugin_manager",
      "plugins.execution.executor_registry",
      "plugins.execution.__init__"
    ]
  },
  {
    "module": "plugins.execution.process_manager",
    "cluster": "Plugins",
    "file_path": "plugins/execution/process_manager.py",
    "classes": [
      {
        "name": "ProcessStatus",
        "methods": []
      },
      {
        "name": "ProcessInfo",
        "methods": []
      },
      {
        "name": "ProcessManager",
        "methods": [
          "__init__",
          "register",
          "update_heartbeat",
          "mark_crashed",
          "unregister",
          "get_process",
          "get_all_processes",
          "restart_process",
          "stop_process"
        ]
      },
      {
        "name": "ProcessMonitor",
        "methods": [
          "__init__",
          "start",
          "stop",
          "_monitor_loop"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "threading",
      "time",
      "enum",
      "dataclasses",
      "typing",
      "datetime"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.execution.subprocess_executor",
      "plugins.plugin_manager",
      "plugins.execution.__init__"
    ]
  },
  {
    "module": "plugins.execution.subprocess_executor",
    "cluster": "Plugins",
    "file_path": "plugins/execution/subprocess_executor.py",
    "classes": [
      {
        "name": "SubprocessExecutor",
        "methods": [
          "__init__",
          "set_process_manager",
          "start",
          "stop",
          "start_plugin",
          "stop_plugin",
          "execute_event",
          "_restart_plugin_process",
          "stop_plugin_by_name"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "multiprocessing",
      "threading",
      "time",
      "plugins.execution.base",
      "plugins.execution.process_manager"
    ],
    "depends_on": [
      "plugins.execution.base",
      "plugins.execution.process_manager"
    ],
    "used_by": [
      "plugins.plugin_manager",
      "plugins.execution.executor_registry",
      "plugins.execution.__init__"
    ]
  },
  {
    "module": "plugins.execution.worker",
    "cluster": "Plugins",
    "file_path": "plugins/execution/worker.py",
    "classes": [],
    "functions": [
      "send_heartbeat",
      "load_plugin",
      "worker_main"
    ],
    "imports": [
      "sys",
      "time",
      "threading",
      "importlib"
    ],
    "depends_on": [],
    "used_by": [
      "plugins.plugin_manager"
    ]
  },
  {
    "module": "plugins.execution.__init__",
    "cluster": "Plugins",
    "file_path": "plugins/execution/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "plugins.execution.base",
      "plugins.execution.inprocess_executor",
      "plugins.execution.subprocess_executor",
      "plugins.execution.executor_registry",
      "plugins.execution.process_manager"
    ],
    "depends_on": [
      "plugins.execution.subprocess_executor",
      "plugins.execution.base",
      "plugins.execution.inprocess_executor",
      "plugins.execution.executor_registry",
      "plugins.execution.process_manager"
    ],
    "used_by": [
      "plugins.plugin_manager"
    ]
  },
  {
    "module": "web.alerts_api",
    "cluster": "Web API",
    "file_path": "web/alerts_api.py",
    "classes": [],
    "functions": [
      "_get_manager",
      "list_alerts",
      "alerts_stats",
      "ack_alert",
      "dismiss_alert",
      "clear_alerts",
      "create_test_alert"
    ],
    "imports": [
      "flask",
      "sys",
      "os",
      "runtime.notifications.notification_manager",
      "runtime.notifications.notification_types"
    ],
    "depends_on": [
      "runtime.notifications.notification_types",
      "runtime.notifications.notification_manager"
    ],
    "used_by": [
      "funpayhub_main"
    ]
  },
  {
    "module": "web.assistant_api",
    "cluster": "Web API",
    "file_path": "web/assistant_api.py",
    "classes": [],
    "functions": [
      "_base_dir",
      "_load_keys",
      "_save_keys",
      "_load_history",
      "_save_history",
      "_gather_context",
      "_kb_lookup",
      "_call_openai",
      "_call_groq",
      "_call_openrouter",
      "get_keys",
      "set_keys",
      "get_history",
      "clear_history",
      "delete_conv",
      "chat",
      "test_provider"
    ],
    "imports": [
      "flask",
      "json",
      "time",
      "pathlib",
      "security.secrets_manager",
      "runtime.http_client"
    ],
    "depends_on": [
      "runtime.http_client",
      "security.secrets_manager"
    ],
    "used_by": [
      "funpayhub_main"
    ]
  },
  {
    "module": "web.funpay_proxy",
    "cluster": "Web API",
    "file_path": "web/funpay_proxy.py",
    "classes": [],
    "functions": [
      "_get_user_id_from_seller_service",
      "_scrape_profile",
      "get_profile",
      "get_me",
      "debug"
    ],
    "imports": [
      "flask",
      "re",
      "time",
      "runtime.http_client"
    ],
    "depends_on": [
      "runtime.http_client"
    ],
    "used_by": [
      "funpayhub_main"
    ]
  },
  {
    "module": "web.health",
    "cluster": "Web API",
    "file_path": "web/health.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "web.logs_api",
    "cluster": "Web API",
    "file_path": "web/logs_api.py",
    "classes": [],
    "functions": [
      "_get_runtime_log",
      "_get_observability",
      "_seed_demo_logs",
      "_read_app_log",
      "list_logs",
      "logs_stats",
      "clear_logs",
      "export_logs",
      "add_test_log",
      "list_events"
    ],
    "imports": [
      "flask",
      "sys",
      "os",
      "json",
      "time",
      "runtime.runtime_log"
    ],
    "depends_on": [
      "runtime.runtime_log"
    ],
    "used_by": [
      "funpayhub_main"
    ]
  },
  {
    "module": "web.plugin_management_api",
    "cluster": "Web API",
    "file_path": "web/plugin_management_api.py",
    "classes": [],
    "functions": [
      "_runtime_controller",
      "_load_history",
      "_save_history",
      "_record_history",
      "_get_plugins_data",
      "get_all_plugins",
      "get_plugin_details",
      "enable_plugin",
      "disable_plugin",
      "restart_plugin",
      "get_plugin_config",
      "update_plugin_config",
      "get_plugin_history",
      "get_dependency_graph",
      "get_plugin_schema",
      "call_plugin_action",
      "get_plugin_logs",
      "reset_plugin_config",
      "plugins_autostart"
    ],
    "imports": [
      "flask",
      "sys",
      "os",
      "json",
      "pathlib",
      "datetime",
      "runtime.plugin_config_manager",
      "runtime.dependency_resolver"
    ],
    "depends_on": [
      "runtime.plugin_config_manager",
      "runtime.dependency_resolver"
    ],
    "used_by": [
      "funpayhub_main"
    ]
  },
  {
    "module": "web.seller_api",
    "cluster": "Web API",
    "file_path": "web/seller_api.py",
    "classes": [],
    "functions": [
      "version",
      "status",
      "set_credentials",
      "delete_credentials",
      "overview",
      "balance",
      "balance_full",
      "balance_history",
      "clear_balance_history",
      "wallets",
      "test_conn",
      "my_lots",
      "lot_details",
      "update_price",
      "toggle_active",
      "bulk_price",
      "raise_cat",
      "sales",
      "orders",
      "chat_messages",
      "send_message",
      "refund",
      "customers",
      "customer_details",
      "account_notifications",
      "collect_notifications",
      "ack_notification",
      "dismiss_notification",
      "clear_notifications",
      "market_categories",
      "market_scan",
      "compare_prices",
      "calculate_optimal",
      "simulate_price",
      "optimize_all",
      "list_competitors",
      "competitor_details",
      "track_competitor",
      "untrack_competitor",
      "get_watchlist",
      "heatmap",
      "list_niches",
      "compare_niche",
      "list_suppliers",
      "get_supplier",
      "add_supplier",
      "delete_supplier",
      "link_lot_supplier",
      "unlink_lot_supplier",
      "lot_suppliers",
      "margin_overview",
      "margin_calc",
      "margin_settings",
      "save_margin_settings",
      "seller_ratings",
      "seller_rating_details",
      "list_market_alerts",
      "collect_market_alerts_endpoint",
      "ack_market_alert",
      "dismiss_market_alert",
      "clear_market_alerts",
      "get_alert_settings",
      "save_alert_settings",
      "list_templates",
      "add_template",
      "delete_template",
      "preview_template",
      "list_rules",
      "save_rule",
      "delete_rule",
      "toggle_rule",
      "autoreply_test",
      "autoreply_log",
      "clear_autoreply_log",
      "autodelivery_settings_get",
      "autodelivery_settings_save",
      "autodelivery_bindings",
      "autodelivery_save_binding",
      "autodelivery_delete_binding",
      "autodelivery_stock_get",
      "autodelivery_stock_add",
      "autodelivery_stock_remove",
      "autodelivery_stock_clear",
      "autodelivery_log_get",
      "autodelivery_log_clear",
      "autodelivery_process",
      "automation_tasks",
      "automation_save_task",
      "automation_toggle",
      "automation_run",
      "automation_log",
      "automation_log_clear",
      "automation_reset",
      "list_backups_endpoint",
      "create_backup_endpoint",
      "restore_backup_endpoint",
      "delete_backup_endpoint",
      "download_backup",
      "system_health",
      "ai_advisor",
      "admin_profit",
      "get_badges_b17",
      "mark_badges_read_b17",
      "sim_new_order_b30",
      "sim_buyer_message_b30",
      "sim_review_b30",
      "sim_full_pipeline_b30",
      "_b35_load",
      "_b35_save",
      "b35_get_messages",
      "b35_clear",
      "b35_buyer_send",
      "b35_seller_send",
      "b35_start_scenario",
      "b35_review",
      "_b50_load_twiboost_services",
      "_b50_categorize_service",
      "b50_scan_niches",
      "b50_budget_estimate",
      "b51_generate_lots",
      "b63_sandbox_confirm",
      "b73_reply_to_review",
      "analyze_niches",
      "generate_from_niches",
      "analyze_niches_deep",
      "analyze_niches_deep_progress",
      "analyze_niches_global",
      "analyze_niches_global_progress",
      "optimize_price",
      "apply_optimal",
      "scheduler_suggestions",
      "twiboost_services",
      "generate_lots_endpoint",
      "system_simulate",
      "deactivate_all_lots",
      "_toggle_lots",
      "deactivate_lots_by_supplier",
      "activate_lots_by_supplier",
      "create_all_lots",
      "suppliers_balance",
      "toggle_auto_lots",
      "system_start",
      "system_stop",
      "ai_status"
    ],
    "imports": [
      "flask",
      "sys",
      "os",
      "runtime.seller_service",
      "runtime.database.models",
      "threading"
    ],
    "depends_on": [
      "runtime.database.models",
      "runtime.seller_service"
    ],
    "used_by": [
      "funpayhub_main"
    ]
  },
  {
    "module": "web.userdata_api",
    "cluster": "Web API",
    "file_path": "web/userdata_api.py",
    "classes": [],
    "functions": [
      "_userdata_root",
      "_safe_filename",
      "upload",
      "list_files",
      "delete",
      "serve_userdata"
    ],
    "imports": [
      "flask",
      "sys",
      "os",
      "uuid",
      "hashlib",
      "pathlib"
    ],
    "depends_on": [],
    "used_by": [
      "funpayhub_main"
    ]
  },
  {
    "module": "bot.api_client",
    "cluster": "Bot",
    "file_path": "bot/api_client.py",
    "classes": [
      {
        "name": "APIClientError",
        "methods": []
      },
      {
        "name": "APIClient",
        "methods": [
          "__init__"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "json",
      "logging",
      "typing",
      "aiohttp",
      "bot.config"
    ],
    "depends_on": [
      "bot.config"
    ],
    "used_by": [
      "bot.services.cache_service",
      "bot.handlers.callbacks"
    ]
  },
  {
    "module": "bot.config",
    "cluster": "Bot",
    "file_path": "bot/config.py",
    "classes": [
      {
        "name": "BotConfig",
        "methods": []
      }
    ],
    "functions": [
      "get_bot_config",
      "get_hub_url"
    ],
    "imports": [
      "__future__",
      "os",
      "dataclasses"
    ],
    "depends_on": [],
    "used_by": [
      "bot.handlers.callbacks",
      "run_bot",
      "bot.middlewares.auth",
      "bot.api_client",
      "bot.handlers.start"
    ]
  },
  {
    "module": "bot.formatters",
    "cluster": "Bot",
    "file_path": "bot/formatters.py",
    "classes": [],
    "functions": [
      "_text",
      "_ts",
      "_safe_float",
      "format_welcome",
      "format_balance",
      "format_report",
      "format_system_status",
      "format_lots",
      "format_lots_stats",
      "format_simulation",
      "format_logs",
      "format_plugins_summary",
      "format_plugin_detail",
      "format_wallet",
      "format_hub_start",
      "format_hub_stop",
      "format_ai_agent",
      "format_ai_recommendation",
      "format_market_status",
      "format_stats",
      "format_system",
      "format_action_ok",
      "format_remove_all_lots",
      "format_auto_create_toggle",
      "format_error"
    ],
    "imports": [
      "__future__",
      "datetime",
      "html",
      "typing",
      "datetime"
    ],
    "depends_on": [],
    "used_by": [
      "run_bot",
      "bot.handlers.start",
      "bot.handlers.notifications",
      "bot.handlers.callbacks"
    ]
  },
  {
    "module": "bot.__init__",
    "cluster": "Bot",
    "file_path": "bot/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "bot.handlers.ai_agent",
    "cluster": "Bot",
    "file_path": "bot/handlers/ai_agent.py",
    "classes": [],
    "functions": [
      "_confirm_keyboard",
      "_get_ai_keyboard"
    ],
    "imports": [
      "__future__",
      "logging",
      "aiogram",
      "aiogram.filters",
      "aiogram.types",
      "bot.services"
    ],
    "depends_on": [
      "bot.services"
    ],
    "used_by": [
      "run_bot"
    ]
  },
  {
    "module": "bot.handlers.callbacks",
    "cluster": "Bot",
    "file_path": "bot/handlers/callbacks.py",
    "classes": [],
    "functions": [
      "_is_local",
      "_get_hub_pid",
      "_is_local",
      "_get_hub_pid"
    ],
    "imports": [
      "__future__",
      "json",
      "logging",
      "os",
      "subprocess",
      "time",
      "typing",
      "psutil",
      "aiogram",
      "aiogram.types",
      "aiogram.exceptions",
      "bot.api_client",
      "bot.config",
      "bot.services.cache_service",
      "bot.formatters",
      "bot.keyboards.main"
    ],
    "depends_on": [
      "bot.services.cache_service",
      "bot.formatters",
      "bot.keyboards.main",
      "bot.api_client",
      "bot.config"
    ],
    "used_by": [
      "run_bot"
    ]
  },
  {
    "module": "bot.handlers.notifications",
    "cluster": "Bot",
    "file_path": "bot/handlers/notifications.py",
    "classes": [],
    "functions": [],
    "imports": [
      "__future__",
      "logging",
      "aiogram",
      "aiogram.types",
      "bot.formatters",
      "bot.keyboards.main"
    ],
    "depends_on": [
      "bot.keyboards.main",
      "bot.formatters"
    ],
    "used_by": [
      "run_bot"
    ]
  },
  {
    "module": "bot.handlers.start",
    "cluster": "Bot",
    "file_path": "bot/handlers/start.py",
    "classes": [],
    "functions": [],
    "imports": [
      "__future__",
      "logging",
      "os",
      "json",
      "bcrypt",
      "aiogram",
      "aiogram.filters",
      "aiogram.types",
      "aiogram.exceptions",
      "bot.formatters",
      "bot.keyboards.main",
      "bot.config"
    ],
    "depends_on": [
      "bot.keyboards.main",
      "bot.formatters",
      "bot.config"
    ],
    "used_by": [
      "run_bot"
    ]
  },
  {
    "module": "bot.keyboards.main",
    "cluster": "Bot",
    "file_path": "bot/keyboards/main.py",
    "classes": [],
    "functions": [
      "get_main_menu",
      "get_lots_menu",
      "get_back_button",
      "get_logs_keyboard",
      "get_plugins_keyboard",
      "get_plugin_detail_keyboard",
      "get_confirm_keyboard",
      "get_refresh_keyboard"
    ],
    "imports": [
      "__future__",
      "aiogram.types"
    ],
    "depends_on": [],
    "used_by": [
      "bot.handlers.callbacks",
      "run_bot",
      "bot.handlers.notifications",
      "bot.handlers.start",
      "bot.keyboards.__init__"
    ]
  },
  {
    "module": "bot.keyboards.__init__",
    "cluster": "Bot",
    "file_path": "bot/keyboards/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "bot.keyboards.main"
    ],
    "depends_on": [
      "bot.keyboards.main"
    ],
    "used_by": []
  },
  {
    "module": "bot.middlewares.auth",
    "cluster": "Bot",
    "file_path": "bot/middlewares/auth.py",
    "classes": [
      {
        "name": "AuthMiddleware",
        "methods": []
      }
    ],
    "functions": [
      "_load_authorized",
      "_is_authorized",
      "_is_public_command"
    ],
    "imports": [
      "__future__",
      "bcrypt",
      "json",
      "logging",
      "os",
      "typing",
      "aiogram",
      "aiogram.types",
      "bot.config"
    ],
    "depends_on": [
      "bot.config"
    ],
    "used_by": [
      "run_bot",
      "bot.middlewares.__init__"
    ]
  },
  {
    "module": "bot.middlewares.__init__",
    "cluster": "Bot",
    "file_path": "bot/middlewares/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "bot.middlewares.auth"
    ],
    "depends_on": [
      "bot.middlewares.auth"
    ],
    "used_by": [
      "run_bot"
    ]
  },
  {
    "module": "bot.services.ai_agent_service",
    "cluster": "Bot",
    "file_path": "bot/services/ai_agent_service.py",
    "classes": [
      {
        "name": "PatchProposal",
        "methods": []
      },
      {
        "name": "AIAgentService",
        "methods": [
          "__init__",
          "configure",
          "is_ready",
          "_is_sensitive_path"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "asyncio",
      "json",
      "logging",
      "os",
      "time",
      "dataclasses",
      "datetime",
      "pathlib",
      "typing",
      "aiohttp",
      "aiogram.types"
    ],
    "depends_on": [],
    "used_by": [
      "bot.services.__init__",
      "bot.handlers.ai_agent",
      "run_bot"
    ]
  },
  {
    "module": "bot.services.cache_service",
    "cluster": "Bot",
    "file_path": "bot/services/cache_service.py",
    "classes": [
      {
        "name": "BotCache",
        "methods": [
          "__init__",
          "register"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "asyncio",
      "logging",
      "time",
      "typing",
      "bot.api_client"
    ],
    "depends_on": [
      "bot.api_client"
    ],
    "used_by": [
      "run_bot",
      "bot.handlers.ai_agent",
      "bot.handlers.callbacks"
    ]
  },
  {
    "module": "bot.services.__init__",
    "cluster": "Bot",
    "file_path": "bot/services/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "bot.services.ai_agent_service"
    ],
    "depends_on": [
      "bot.services.ai_agent_service"
    ],
    "used_by": [
      "run_bot",
      "bot.handlers.ai_agent"
    ]
  },
  {
    "module": "FunPayAPI.account",
    "cluster": "FunPayAPI",
    "file_path": "FunPayAPI/account.py",
    "classes": [
      {
        "name": "Account",
        "methods": [
          "__init__",
          "method",
          "get",
          "runner_request",
          "get_payload_data",
          "abuse_runner",
          "get_subcategory_public_lots",
          "get_my_subcategory_lots",
          "get_lot_page",
          "get_balance",
          "get_chat_history",
          "parse_chats_histories",
          "get_chats_histories",
          "upload_image",
          "send_message",
          "send_image",
          "send_review",
          "delete_review",
          "refund",
          "withdraw",
          "get_raise_modal",
          "raise_lots",
          "get_user",
          "get_chat",
          "get_order_shortcut",
          "get_orders_by_ids",
          "get_order",
          "get_sales",
          "get_sells",
          "add_chats",
          "request_chats",
          "get_chats",
          "get_chat_by_name",
          "get_chat_by_id",
          "calc",
          "get_lot_fields",
          "get_chip_fields",
          "save_offer",
          "save_chip",
          "save_lot",
          "delete_lot",
          "get_exchange_rate",
          "get_buyer_viewing",
          "get_buyers_viewing",
          "get_wallets",
          "save_wallets",
          "get_category",
          "categories",
          "get_sorted_categories",
          "get_subcategory",
          "subcategories",
          "get_sorted_subcategories",
          "logout",
          "is_initiated",
          "__setup_categories",
          "__parse_messages",
          "__update_csrf_token",
          "__parse_buyer_viewing",
          "__parse_order",
          "chat_id_private",
          "bot_character",
          "old_bot_character",
          "zero_width_suffix",
          "locale",
          "locale",
          "normalize_url",
          "is_funpay_api_method"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "html",
      "typing",
      "FunPayAPI.common.enums",
      "FunPayAPI.common.utils",
      "types",
      "requests_toolbelt",
      "bs4",
      "datetime",
      "requests",
      "logging",
      "random",
      "string",
      "json",
      "time",
      "re",
      "requests.adapters",
      "urllib3.util.retry",
      "common"
    ],
    "depends_on": [
      "FunPayAPI.common.enums",
      "FunPayAPI.common.utils"
    ],
    "used_by": []
  },
  {
    "module": "FunPayAPI.types",
    "cluster": "FunPayAPI",
    "file_path": "FunPayAPI/types.py",
    "classes": [
      {
        "name": "BaseOrderInfo",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "ChatShortcut",
        "methods": [
          "__init__",
          "get_last_message_type",
          "__str__"
        ]
      },
      {
        "name": "BuyerViewing",
        "methods": [
          "__init__",
          "lot_id",
          "subcategory_type"
        ]
      },
      {
        "name": "Chat",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "Message",
        "methods": [
          "__init__",
          "get_message_type",
          "__str__"
        ]
      },
      {
        "name": "OrderShortcut",
        "methods": [
          "__init__",
          "parse_amount",
          "__str__"
        ]
      },
      {
        "name": "Server",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "Side",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "Order",
        "methods": [
          "__init__",
          "get_field",
          "get_field_value",
          "get_field_value_any",
          "short_description",
          "title",
          "full_description",
          "payment_msg",
          "lot_params",
          "lot_params_text",
          "lot_params_dict",
          "character_name",
          "__str__"
        ]
      },
      {
        "name": "Category",
        "methods": [
          "__init__",
          "add_subcategory",
          "get_subcategory",
          "get_subcategories",
          "get_sorted_subcategories"
        ]
      },
      {
        "name": "SubCategory",
        "methods": [
          "__init__",
          "is_common",
          "is_lots",
          "is_currency",
          "is_chips",
          "ui_name",
          "telegram_text"
        ]
      },
      {
        "name": "LotField",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "LotFields",
        "methods": [
          "__init__",
          "amount",
          "amount",
          "public_link",
          "private_link",
          "fields",
          "edit_fields",
          "set_fields",
          "renew_fields"
        ]
      },
      {
        "name": "ChipOffer",
        "methods": [
          "__init__",
          "key"
        ]
      },
      {
        "name": "ChipFields",
        "methods": [
          "__init__",
          "fields",
          "renew_fields",
          "__parse_offers"
        ]
      },
      {
        "name": "LotPage",
        "methods": [
          "__init__",
          "seller_url"
        ]
      },
      {
        "name": "SellerShortcut",
        "methods": [
          "__init__",
          "link"
        ]
      },
      {
        "name": "LotShortcut",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "MyLotShortcut",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "UserProfile",
        "methods": [
          "__init__",
          "get_lot",
          "get_lots",
          "get_sorted_lots",
          "get_sorted_lots",
          "get_sorted_lots",
          "get_sorted_lots",
          "update_lot",
          "add_lot",
          "get_common_lots",
          "get_currency_lots",
          "__str__"
        ]
      },
      {
        "name": "Review",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "Balance",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "PaymentMethod",
        "methods": [
          "__init__"
        ]
      },
      {
        "name": "CalcResult",
        "methods": [
          "__init__",
          "get_coefficient",
          "commission_coefficient",
          "commission_percent"
        ]
      },
      {
        "name": "Wallet",
        "methods": [
          "__init__"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "re",
      "typing",
      "FunPayAPI.common.enums",
      "common.utils",
      "common.enums",
      "datetime"
    ],
    "depends_on": [
      "FunPayAPI.common.enums"
    ],
    "used_by": []
  },
  {
    "module": "FunPayAPI.__init__",
    "cluster": "FunPayAPI",
    "file_path": "FunPayAPI/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [
      "account",
      "common"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "FunPayAPI.common.enums",
    "cluster": "FunPayAPI",
    "file_path": "FunPayAPI/common/enums.py",
    "classes": [
      {
        "name": "EventTypes",
        "methods": []
      },
      {
        "name": "MessageTypes",
        "methods": []
      },
      {
        "name": "OrderStatuses",
        "methods": []
      },
      {
        "name": "SubCategoryTypes",
        "methods": []
      },
      {
        "name": "Currency",
        "methods": [
          "__str__",
          "code"
        ]
      },
      {
        "name": "Wallet",
        "methods": []
      }
    ],
    "functions": [],
    "imports": [
      "__future__",
      "enum"
    ],
    "depends_on": [],
    "used_by": [
      "FunPayAPI.account",
      "FunPayAPI.types"
    ]
  },
  {
    "module": "FunPayAPI.common.exceptions",
    "cluster": "FunPayAPI",
    "file_path": "FunPayAPI/common/exceptions.py",
    "classes": [
      {
        "name": "AccountNotInitiatedError",
        "methods": [
          "__init__",
          "__str__"
        ]
      },
      {
        "name": "RequestFailedError",
        "methods": [
          "__init__",
          "short_str",
          "__str__"
        ]
      },
      {
        "name": "UnauthorizedError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "WithdrawError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "RaiseError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "ImageUploadError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "MessageNotDeliveredError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "FeedbackEditingError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "LotParsingError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "LotSavingError",
        "methods": [
          "__init__",
          "short_str"
        ]
      },
      {
        "name": "RefundError",
        "methods": [
          "__init__",
          "short_str"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "requests"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "FunPayAPI.common.utils",
    "cluster": "FunPayAPI",
    "file_path": "FunPayAPI/common/utils.py",
    "classes": [
      {
        "name": "RegularExpressions",
        "methods": [
          "__new__",
          "__init__"
        ]
      }
    ],
    "functions": [
      "random_tag",
      "parse_wait_time",
      "parse_currency",
      "parse_funpay_datetime"
    ],
    "imports": [
      "string",
      "random",
      "re",
      "datetime",
      "enums"
    ],
    "depends_on": [],
    "used_by": [
      "FunPayAPI.account"
    ]
  },
  {
    "module": "FunPayAPI.common.__init__",
    "cluster": "FunPayAPI",
    "file_path": "FunPayAPI/common/__init__.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "security.secrets_manager",
    "cluster": "Security",
    "file_path": "security/secrets_manager.py",
    "classes": [
      {
        "name": "SecretsManager",
        "methods": [
          "__init__",
          "encrypt_secret",
          "decrypt_secret",
          "get_encryption_key",
          "get_secret",
          "set_secret",
          "delete_secret",
          "_load_store",
          "_save_store",
          "rotate_key"
        ]
      }
    ],
    "functions": [
      "_project_root",
      "_dotenv_path",
      "_load_key_from_dotenv",
      "_save_key_to_dotenv",
      "_resolve_key"
    ],
    "imports": [
      "json",
      "os",
      "re",
      "logging",
      "pathlib",
      "typing",
      "cryptography.fernet"
    ],
    "depends_on": [],
    "used_by": [
      "migrate_secrets",
      "web.assistant_api",
      "runtime.ai_team.model_manager",
      "plugins.plugin_base",
      "hub_bootstrap"
    ]
  },
  {
    "module": "security.secret_loader",
    "cluster": "Security",
    "file_path": "security/secret_loader.py",
    "classes": [],
    "functions": [],
    "imports": [],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "eventbus",
    "cluster": "Other",
    "file_path": "eventbus.py",
    "classes": [
      {
        "name": "EventBus",
        "methods": [
          "__init__",
          "subscribe",
          "unsubscribe",
          "emit",
          "publish"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "threading",
      "typing",
      "collections"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "funpayhub_main",
    "cluster": "Other",
    "file_path": "funpayhub_main.py",
    "classes": [],
    "functions": [
      "_health",
      "_api_version",
      "_require_api_token",
      "_is_headless",
      "_handle_sigterm",
      "run_flask",
      "main"
    ],
    "imports": [
      "sys",
      "os",
      "io",
      "datetime",
      "sys",
      "os",
      "threading",
      "time",
      "logging",
      "signal",
      "pathlib",
      "flask",
      "web.plugin_management_api",
      "web.alerts_api",
      "web.logs_api",
      "web.seller_api",
      "web.userdata_api",
      "web.funpay_proxy",
      "web.assistant_api"
    ],
    "depends_on": [
      "web.alerts_api",
      "web.userdata_api",
      "web.funpay_proxy",
      "web.plugin_management_api",
      "web.assistant_api",
      "web.logs_api",
      "web.seller_api"
    ],
    "used_by": []
  },
  {
    "module": "hub_bootstrap",
    "cluster": "Other",
    "file_path": "hub_bootstrap.py",
    "classes": [
      {
        "name": "HubStateAPI",
        "methods": [
          "__init__",
          "_fetch",
          "get_state",
          "get_balance",
          "get_withdrawable",
          "get_lots",
          "get_total_lots",
          "get_active_lots",
          "get_profile",
          "get_username",
          "get_user_id",
          "get_status",
          "get_last_update",
          "get_logs",
          "is_online",
          "to_dict"
        ]
      }
    ],
    "functions": [
      "_start_background_worker",
      "init_plugin_system",
      "_start_market_auto_update",
      "_do_market_update",
      "_start_auto_backup",
      "_do_auto_backup",
      "_notify_telegram",
      "_start_health_check",
      "_run_health_check"
    ],
    "imports": [
      "dotenv",
      "os",
      "time",
      "json",
      "re",
      "threading",
      "typing",
      "logging",
      "runtime.http_client",
      "security.secrets_manager"
    ],
    "depends_on": [
      "runtime.http_client",
      "security.secrets_manager"
    ],
    "used_by": []
  },
  {
    "module": "migrate_secrets",
    "cluster": "Other",
    "file_path": "migrate_secrets.py",
    "classes": [],
    "functions": [
      "migrate_config_file",
      "main"
    ],
    "imports": [
      "os",
      "configparser",
      "security.secrets_manager"
    ],
    "depends_on": [
      "security.secrets_manager"
    ],
    "used_by": []
  },
  {
    "module": "run_bot",
    "cluster": "Other",
    "file_path": "run_bot.py",
    "classes": [],
    "functions": [],
    "imports": [
      "asyncio",
      "logging",
      "os",
      "sys",
      "dotenv",
      "aiogram",
      "aiogram.enums",
      "aiogram.client.default",
      "aiohttp",
      "bot.config",
      "bot.middlewares",
      "bot.handlers.start",
      "bot.handlers.callbacks",
      "bot.handlers.notifications",
      "bot.handlers.ai_agent",
      "bot.keyboards.main",
      "bot.formatters",
      "bot.services",
      "bot.services.cache_service"
    ],
    "depends_on": [
      "bot.handlers.ai_agent",
      "bot.services.cache_service",
      "bot.services",
      "bot.formatters",
      "bot.middlewares",
      "bot.handlers.callbacks",
      "bot.keyboards.main",
      "bot.handlers.notifications",
      "bot.handlers.start",
      "bot.config"
    ],
    "used_by": []
  },
  {
    "module": "state_api",
    "cluster": "Other",
    "file_path": "state_api.py",
    "classes": [
      {
        "name": "StateAPI",
        "methods": [
          "__init__",
          "_get_state",
          "_get_lock",
          "get_state",
          "get_field",
          "get_balance",
          "get_withdrawable",
          "get_lots",
          "get_total_lots",
          "get_active_lots",
          "get_profile",
          "get_username",
          "get_user_id",
          "get_status",
          "get_last_update",
          "get_logs",
          "is_online",
          "to_dict"
        ]
      }
    ],
    "functions": [],
    "imports": [
      "time",
      "typing",
      "copy"
    ],
    "depends_on": [],
    "used_by": []
  },
  {
    "module": "test_real_lot",
    "cluster": "Other",
    "file_path": "test_real_lot.py",
    "classes": [],
    "functions": [],
    "imports": [
      "os",
      "sys",
      "json",
      "subprocess",
      "time",
      "urllib.request",
      "urllib.error",
      "pathlib"
    ],
    "depends_on": [],
    "used_by": []
  }
];