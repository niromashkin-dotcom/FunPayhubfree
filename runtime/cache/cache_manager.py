"""
CacheManager — лёгкий in-memory TTL-кэш (Этап 2.4).

Используется слоем Telegram-бота для кэширования ответов Hub с
фоновым обновлением, чтобы не дёргать HTTP при каждом нажатии кнопки.
Потокобезопасен (RLock). НЕ персистентен (достаточно для сессии бота).
"""
from __future__ import annotations

import time
from threading import RLock


class CacheManager:
    """Простой TTL-кэш ключ → значение."""

    def __init__(self, default_ttl: float = 30.0):
        self._store: dict = {}
        self._lock = RLock()
        self._default_ttl = default_ttl

    def get(self, key: str):
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            value, exp = item
            if exp is not None and time.time() > exp:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value, ttl: float | None = None) -> None:
        ttl = self._default_ttl if ttl is None else ttl
        with self._lock:
            self._store[key] = (value, time.time() + ttl if ttl else None)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._store)
