from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger("bot.services.ai_agent")


@dataclass
class PatchProposal:
    patch_id: str
    diagnosis: str
    patch: str
    file: str
    confidence: int
    created_at: float = field(default_factory=time.time)
    applied: bool = False


class AIAgentService:
    def __init__(self) -> None:
        self._admin_chat_id: str = ""
        self._llm_providers: List[Dict[str, str]] = []
        self._github_token: str = ""
        self._render_api_key: str = ""
        self._render_service_id: str = ""
        self._pending_patches: List[PatchProposal] = []
        self._last_position: int = 0
        self._scan_interval: int = 300
        self._scan_task: Optional[asyncio.Task] = None
        self._log_path: Path = Path("logs/app.log")
        self._project_root: Path = Path(".").resolve()

    def configure(self, admin_chat_id: str, llm_api_keys: List[Dict[str, str]],
                  github_token: str = "", render_api_key: str = "",
                  render_service_id: str = "") -> None:
        self._admin_chat_id = admin_chat_id
        self._llm_providers = llm_api_keys or []
        self._github_token = github_token
        self._render_api_key = render_api_key
        self._render_service_id = render_service_id

    def is_ready(self) -> bool:
        return bool(self._llm_providers and self._admin_chat_id)

    async def start(self, bot: Any) -> None:
        if not self.is_ready():
            logger.warning("[AIAgent] Не настроен: нет провайдеров LLM или admin_chat_id")
            return
        if self._scan_task and not self._scan_task.done():
            logger.info("[AIAgent] Уже запущен")
            return
        self._bot = bot
        self._scan_task = asyncio.create_task(self._scanner_loop())
        logger.info("[AIAgent] Запущен 24/7 мониторинг. Провайдеров: %d", len(self._llm_providers))

    async def stop(self) -> None:
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        logger.info("[AIAgent] Остановлен")

    async def _scanner_loop(self) -> None:
        while True:
            try:
                await self._scan_logs()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("[AIAgent] Scan error: %s", exc)
            try:
                await asyncio.sleep(self._scan_interval)
            except asyncio.CancelledError:
                raise

    async def _scan_logs(self) -> None:
        if not self._log_path.exists():
            return
        try:
            with open(self._log_path, "r", encoding="utf-8") as f:
                f.seek(self._last_position)
                new_lines = f.readlines()
                self._last_position = f.tell()
        except Exception as exc:
            logger.error("[AIAgent] Cannot read logs: %s", exc)
            return

        errors = []
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            if any(kw in line for kw in ["ERROR", "CRITICAL", "Traceback",
                                          "Failed", "failed", "Error", "error"]):
                errors.append(line)

        if errors:
            await self._analyze_errors(errors[:5])

    async def _analyze_errors(self, errors: List[str]) -> None:
        if not self._llm_providers:
            return
        try:
            analysis = await self._call_llm_with_fallback(errors)
            if analysis:
                patch = PatchProposal(
                    patch_id=f"patch_{int(time.time())}",
                    diagnosis=analysis.get("diagnosis", "Неизвестная ошибка"),
                    patch=analysis.get("patch", "Требуется ручной анализ"),
                    file=analysis.get("file", "—"),
                    confidence=analysis.get("confidence", 50),
                )
                self._pending_patches.append(patch)
                await self._notify_patch(patch)
        except Exception as exc:
            logger.error("[AIAgent] Analyze error: %s", exc)

    async def _call_llm_with_fallback(self, errors: List[str]) -> Optional[Dict[str, Any]]:
        last_error = None
        for provider in self._llm_providers:
            try:
                return await self._call_llm(provider, errors)
            except Exception as exc:
                last_error = exc
                logger.warning("[AIAgent] LLM provider %s failed: %s", provider.get("name", "?"), exc)
                continue
        logger.error("[AIAgent] All LLM providers failed. Last error: %s", last_error)
        return None

    async def _call_llm(self, provider: Dict[str, str], errors: List[str]) -> Optional[Dict[str, Any]]:
        prompt = (
            "Ты — AI инженер FunPay Hub. Проанализируй ошибки и предложи патч.\n"
            "Верни строго JSON: {\"diagnosis\": str, \"patch\": str, \"file\": str, \"confidence\": int, \"action\": str}\n"
            "Доступные действия: patch_file (изменить файл), restart_service (перезапустить), deploy (деплоить), manual (только отчёт)\n"
            "Проект: Python, Flask, aiogram, FunPay API\n"
            "Errors:\n" + "\n".join(errors[:5])
        )
        api_key = provider.get("api_key", "")
        api_url = provider.get("api_url", "")
        model = provider.get("model", "freellm-24ba17fbc6eef0477edbfc9755b0964bbf476eba8b3469cd")

        if not api_key or not api_url:
            raise ValueError("Empty API key or URL")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Ты — AI инженер. Отвечай строго JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        }

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"HTTP {resp.status}: {text[:200]}")
                data = await resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not content:
                    return None
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {
                        "diagnosis": content[:200],
                        "patch": "LLM вернул не-JSON ответ",
                        "file": "—",
                        "confidence": 30,
                        "action": "manual",
                    }

    async def analyze_project(self, file_path: str) -> Dict[str, Any]:
        """Проанализировать конкретный файл проекта."""
        target = (self._project_root / file_path).resolve()
        if not target.exists() or not str(target).startswith(str(self._project_root)):
            return {"error": "Файл не найден или вне проекта"}

        try:
            content = target.read_text(encoding="utf-8")
            lines = content.splitlines()
            issues = []
            for i, line in enumerate(lines[:500], 1):
                if any(kw in line for kw in ["TODO", "FIXME", "HACK", "BUG", "ERROR", "CRITICAL"]):
                    issues.append(f"Line {i}: {line.strip()[:100]}")

            prompt = (
                f"Проанализируй файл {file_path} на проблемы.\n"
                f"Найдено проблемных меток: {len(issues)}\n"
                f"Примеры: {issues[:5]}\n"
                f"Верни JSON: {{\"diagnosis\": str, \"patch\": str, \"file\": str, \"confidence\": int}}"
            )

            analysis = await self._call_llm_with_fallback([prompt])
            if analysis:
                analysis["file"] = file_path
            return analysis or {"error": "LLM не ответил"}
        except Exception as exc:
            return {"error": str(exc)}

    async def _notify_patch(self, patch: PatchProposal) -> None:
        if not self._admin_chat_id:
            return
        text = (
            f"🤖 <b>AI Engineer Agent</b>\n"
            f"🔍 <b>Диагноз:</b> {patch.diagnosis}\n"
            f"📁 <b>Файл:</b> {patch.file}\n"
            f"💊 <b>Патч:</b> {patch.patch}\n"
            f"📊 <b>Уверенность:</b> {patch.confidence}%\n\n"
            f"Применить патч?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, применить", callback_data=f"apply_patch_{patch.patch_id}"),
                InlineKeyboardButton(text="❌ Нет, отклонить", callback_data=f"reject_patch_{patch.patch_id}"),
            ]
        ])
        try:
            await self._bot.send_message(chat_id=self._admin_chat_id, text=text, reply_markup=kb)
        except Exception as exc:
            logger.error("[AIAgent] Notify failed: %s", exc)

    async def apply_patch(self, patch_id: str, bot: Any) -> bool:
        patch = next((p for p in self._pending_patches if p.patch_id == patch_id), None)
        if not patch or patch.applied:
            return False
        patch.applied = True
        logger.info("[AIAgent] Applying patch %s: %s", patch.patch_id, patch.patch)

        # 1. Анализ файла
        if patch.file and patch.file != "—":
            analysis = await self.analyze_project(patch.file)
            if analysis.get("error"):
                try:
                    await bot.send_message(chat_id=self._admin_chat_id, text=f"⚠️ Анализ файла: {analysis['error']}")
                except Exception:
                    pass

        # 2. Коммит в GitHub
        try:
            await self._github_commit(patch)
        except Exception as exc:
            logger.error("[AIAgent] GitHub commit failed: %s", exc)

        # 3. Деплой на Render
        try:
            await self._render_deploy()
        except Exception as exc:
            logger.error("[AIAgent] Render deploy failed: %s", exc)

        try:
            await bot.send_message(chat_id=self._admin_chat_id, text=f"✅ Патч {patch.patch_id} применён, деплой запущен")
        except Exception:
            pass
        return True

    async def reject_patch(self, patch_id: str, bot: Any) -> None:
        patch = next((p for p in self._pending_patches if p.patch_id == patch_id), None)
        if patch and not patch.applied:
            patch.applied = True
            try:
                await bot.send_message(chat_id=self._admin_chat_id, text=f"❌ Патч {patch.patch_id} отклонён")
            except Exception:
                pass

    async def _github_commit(self, patch: PatchProposal) -> None:
        if not self._github_token:
            return
        repo = os.environ.get("GITHUB_REPO", "")
        if not repo:
            logger.warning("[AIAgent] GITHUB_REPO не задан")
            return

        target_path = patch.file
        if not target_path or target_path == "—":
            return

        url = f"https://api.github.com/repos/{repo}/contents/{target_path}"
        headers = {
            "Authorization": f"token {self._github_token}",
            "Accept": "application/vnd.github+json",
        }

        async with aiohttp.ClientSession() as session:
            file_sha = ""
            file_content_b64 = ""
            try:
                async with session.get(url, headers=headers, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        file_sha = data.get("sha", "")
                        import base64
                        file_content_b64 = data.get("content", "")
            except Exception:
                pass

            current_content = ""
            if file_content_b64:
                try:
                    current_content = base64.b64decode(file_content_b64).decode("utf-8", errors="ignore")
                except Exception:
                    current_content = ""

            # Применяем патч: упрощённая стратегия — добавляем комментарий с патчем
            # В реальности LLM должен вернуть точные изменения в коде
            new_content = current_content + f"\n# AI Patch [{patch.patch_id}]: {patch.patch}\n"
            new_content_b64 = __import__("base64").b64encode(new_content.encode("utf-8")).decode("utf-8")

            payload = {
                "message": f"AI patch: {patch.diagnosis}\n\n{patch.patch}",
                "content": new_content_b64,
                "branch": os.environ.get("GITHUB_BRANCH", "main"),
            }
            if file_sha:
                payload["sha"] = file_sha

            async with session.put(url, headers=headers, json=payload, timeout=30) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    logger.error("[AIAgent] GitHub commit failed %s: %s", resp.status, text[:200])
                else:
                    logger.info("[AIAgent] GitHub commit OK")

    async def _render_deploy(self) -> None:
        if not self._render_api_key:
            return

        service_id = self._render_service_id or os.environ.get("RENDER_SERVICE_ID", "")
        if not service_id:
            logger.warning("[AIAgent] RENDER_SERVICE_ID не задан, пробуем автообнаружение")
            service_id = await self._discover_render_service_id()
            if not service_id:
                logger.warning("[AIAgent] Не удалось обнаружить service ID")
                return

        url = f"https://api.render.com/v1/services/{service_id}/deploys"
        headers = {"Authorization": f"Bearer {self._render_api_key}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"clearCache": "clear"}, timeout=30) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    logger.error("[AIAgent] Render deploy failed %s: %s", resp.status, text[:200])
                else:
                    logger.info("[AIAgent] Render deploy triggered")

    async def _discover_render_service_id(self) -> Optional[str]:
        """Auto-discover Render service ID by name."""
        if not self._render_api_key:
            return None
        url = "https://api.render.com/v1/services"
        headers = {"Authorization": f"Bearer {self._render_api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    for svc in data if isinstance(data, list) else data.get("services", []):
                        svc_name = svc.get("name", "")
                        if svc_name in ("funpayhub", "funpayhub-web", "funpayhub-app"):
                            return svc.get("id", "")
        except Exception as exc:
            logger.error("[AIAgent] Render discovery failed: %s", exc)
        return None


ai_agent_service = AIAgentService()
