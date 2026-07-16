from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from bot.config import get_bot_config

logger = logging.getLogger("bot.api_client")


class APIClientError(Exception):
    pass


class APIClient:
    def __init__(self) -> None:
        self._cfg = get_bot_config()
        self._base = self._cfg.hub_url.rstrip("/")
        self._headers: dict[str, str] = {}
        if self._cfg.api_token:
            self._headers["X-API-Token"] = self._cfg.api_token
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=float(__import__("os").environ.get("FUNPAYHUB_API_TIMEOUT", "15")))
            self._session = aiohttp.ClientSession(headers=self._headers, timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, path: str, payload: Any = None) -> Any:
        url = self._base + path
        session = await self._get_session()
        try:
            if method == "GET":
                async with session.get(url) as resp:
                    text = await resp.text()
                    if resp.status == 200:
                        return json.loads(text) if text else {}
                    raise APIClientError(f"HTTP {resp.status}: {text[:200]}")
            else:
                async with session.post(url, json=payload or {}, headers={"Content-Type": "application/json"}) as resp:
                    text = await resp.text()
                    if resp.status in (200, 201):
                        return json.loads(text) if text else {}
                    raise APIClientError(f"HTTP {resp.status}: {text[:200]}")
        except aiohttp.ClientError as exc:
            raise APIClientError(f"Hub недоступен: {exc}") from exc
        except Exception as exc:
            raise APIClientError(f"Ошибка запроса: {exc}") from exc

    async def get(self, path: str) -> Any:
        return await self._request("GET", path)

    async def post(self, path: str, payload: Any = None) -> Any:
        return await self._request("POST", path, payload)


api_client = APIClient()
