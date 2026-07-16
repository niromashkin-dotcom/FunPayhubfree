import sys

file_path = r"d:\Projects\FunPayHub\runtime\seller_service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_get_chat = """    def get_chat_messages(self, chat_id, limit: int = 50) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"available": False, "error": self._last_error or "Нет авторизации", "messages": []}
            try:
                raw = acc.get_chat_history(chat_id)
                messages = []
                items = raw if isinstance(raw, list) else []
                for m in items[-limit:]:
                    text = getattr(m, "text", "") or ""
                    author = getattr(m, "author", "") or getattr(m, "author_id", "")
                    author_id = getattr(m, "author_id", None)
                    mid = getattr(m, "id", None)
                    is_my = bool(getattr(m, "by_bot", False)) or (author_id == acc.id)
                    messages.append({
                        "id": mid,
                        "text": str(text)[:1000],
                        "author": str(author),
                        "author_id": author_id,
                        "is_my": is_my
                    })
                return {"available": True, "messages": messages, "count": len(messages)}
            except Exception as e:
                return {"available": False, "error": _safe_error(e), "messages": []}"""

new_get_chat = """    def get_chat_messages(self, chat_id, limit: int = 50) -> dict:
        with self._lock:
            try:
                raw = self.order_service.chat_service.get_messages(chat_id)
                messages = []
                items = raw if isinstance(raw, list) else []
                acc = self._get_account()
                acc_id = acc.id if acc else None
                for m in items[-limit:]:
                    text = getattr(m, "text", "") or ""
                    author = getattr(m, "author", "") or getattr(m, "author_id", "")
                    author_id = getattr(m, "author_id", None)
                    mid = getattr(m, "id", None)
                    is_my = bool(getattr(m, "by_bot", False)) or (author_id == acc_id)
                    messages.append({
                        "id": mid,
                        "text": str(text)[:1000],
                        "author": str(author),
                        "author_id": author_id,
                        "is_my": is_my
                    })
                return {"available": True, "messages": messages, "count": len(messages)}
            except Exception as e:
                return {"available": False, "error": str(e), "messages": []}"""

old_send_chat = """    def send_chat_message(self, chat_id, text: str, dry_run: bool = True) -> dict:
        with self._lock:
            acc = self._get_account()
            if acc is None:
                return {"ok": False, "error": self._last_error or "Нет авторизации"}
            if not text or not text.strip():
                return {"ok": False, "error": "Пустое сообщение"}
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "chat_id": chat_id, "text": text}
                acc.send_message(chat_id, text=text)
                return {"ok": True, "dry_run": False, "chat_id": chat_id, "text": text}
            except Exception as e:
                return {"ok": False, "error": _safe_error(e)}"""

new_send_chat = """    def send_chat_message(self, chat_id, text: str, dry_run: bool = True) -> dict:
        with self._lock:
            if not text or not text.strip():
                return {"ok": False, "error": "Пустое сообщение"}
            try:
                if dry_run:
                    return {"ok": True, "dry_run": True, "chat_id": chat_id, "text": text}
                
                # FACADE: delegating to ChatService
                self.order_service.chat_service.send_message(chat_id, text)
                return {"ok": True, "dry_run": False, "chat_id": chat_id, "text": text}
            except Exception as e:
                return {"ok": False, "error": str(e)}"""

if old_get_chat in content:
    content = content.replace(old_get_chat, new_get_chat)
else:
    print("Error: get_chat_messages not found")

if old_send_chat in content:
    content = content.replace(old_send_chat, new_send_chat)
else:
    print("Error: send_chat_message not found")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patch applied successfully")
