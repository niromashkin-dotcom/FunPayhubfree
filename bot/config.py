from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    token: str
    admin_chat_id: str
    hub_url: str
    api_token: str | None = None


def get_bot_config() -> BotConfig:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    admin_chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "6934895652").strip()
    hub_url = os.environ.get("FUNPAYHUB_APP_URL", "http://127.0.0.1:5000").strip()
    api_token = os.environ.get("FUNPAYHUB_API_TOKEN", "").strip() or None

    if not token:
        try:
            cfg_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "configs",
                "plugins",
                "telegram_notifier_plugin.json",
            )
            with open(cfg_path, "r", encoding="utf-8") as f:
                import json

                cfg = json.load(f)
            token = cfg.get("bot_token", "").strip()
            if not admin_chat_id or admin_chat_id == "6934895652":
                admin_chat_id = cfg.get("chat_id", admin_chat_id).strip()
        except Exception:
            pass

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Set env var or configs/plugins/telegram_notifier_plugin.json"
        )

    return BotConfig(
        token=token,
        admin_chat_id=admin_chat_id,
        hub_url=hub_url,
        api_token=api_token,
    )
