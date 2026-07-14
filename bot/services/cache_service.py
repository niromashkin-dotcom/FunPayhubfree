"""
Bot-side CacheManager integration (Этап 2.4).

Кэширует ответы Hub по часто используемым GET-эндпоинтам и обновляет их
фоновым циклом, чтобы Telegram-кнопки не дёргали HTTP при каждом нажатии.
При промахе кэша — живой запрос к Hub (fallback прозрачный).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Tuple

from bot.api_client import api_client

logger = logging.getLogger("bot.cache")


class BotCache:
    def __init__(self, default_ttl: float = 30.0):
        self._cache: Dict[str, Tuple[float, object]] = {}  # key -> (exp, value)
        self._paths: Dict[str, Tuple[str, float, bool]] = {}  # key -> (path, ttl, force)
        self._lock = asyncio.Lock()
        self.default_ttl = default_ttl

    def register(self, key: str, path: str, ttl: float | None = None, force: bool = False) -> None:
        self._paths[key] = (path, ttl if ttl is not None else self.default_ttl, force)

    async def get(self, key: str, path: str | None = None, ttl: float | None = None, force: bool = False):
        if path is None:
            if key not in self._paths:
                raise KeyError(f"unregistered cache key: {key}")
            path, ttl, force = self._paths[key]
        now = time.time()
        async with self._lock:
            item = self._cache.get(key)
            if item and now < item[0] and not force:
                return item[1]
        if force:
            sep = "&" if "?" in path else "?"
            path = f"{path}{sep}force=true"
        data = await api_client.get(path)  # промах → живой запрос (fallback)
        async with self._lock:
            self._cache[key] = (now + (ttl if ttl is not None else self.default_ttl), data)
        return data

    async def refresh_all(self) -> None:
        for key, (path, ttl, force) in list(self._paths.items()):
            try:
                await self.get(key, path=path, ttl=ttl, force=force)
            except Exception as exc:  # фоновое обновление не должно падать
                logger.warning("cache refresh %s failed: %s", key, exc)

    async def refresh_loop(self, interval: float = 30.0) -> None:
        while True:
            await asyncio.sleep(interval)
            await self.refresh_all()


# Предзарегистрированные ключи (читаются из кэша с фоновым обновлением)
bot_cache = BotCache(default_ttl=30.0)
bot_cache.register("balance", "/api/seller/balance/full", ttl=30, force=True)
bot_cache.register("overview", "/api/seller/overview", ttl=30, force=True)
bot_cache.register("lots", "/api/seller/lots", ttl=30, force=True)
bot_cache.register("health", "/api/system/health", ttl=20, force=False)
bot_cache.register("plugins", "/api/plugins", ttl=30, force=False)
