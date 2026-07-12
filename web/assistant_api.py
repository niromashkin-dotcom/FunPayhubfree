"""
FunPay Hub - AI Assistant API
Hybrid chat: OpenAI -> Groq -> Local knowledge base
Stores conversation history in configs/assistant_history.json
Stores non-secret assistant settings in configs/assistant_keys.json
API keys are loaded from environment or encrypted store via SecretsManager.
"""
from flask import Blueprint, jsonify, request
import json, time
from pathlib import Path
from security.secrets_manager import SecretsManager

from runtime.http_client import HTTPClient, HTTPClientError

_http_client = HTTPClient()

assistant_bp = Blueprint("assistant", __name__)

# ----------------------------------------------------------------------------
# Storage paths (next to .exe or main script)
# ----------------------------------------------------------------------------

def _base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    here = Path(__file__).resolve()
    for parent in [here.parent.parent, here.parent.parent.parent]:
        if (parent / "funpayhub_main.py").exists():
            return parent
    return here.parent.parent

CONFIGS = _base_dir() / "configs"
CONFIGS.mkdir(parents=True, exist_ok=True)

KEYS_FILE    = CONFIGS / "assistant_keys.json"
HISTORY_FILE = CONFIGS / "assistant_history.json"
SECRETS = SecretsManager()


# ----------------------------------------------------------------------------
# Key management
# ----------------------------------------------------------------------------

def _load_keys() -> dict:
    defaults = {"openai": "", "groq": "", "openrouter": "", "provider": "auto", "model": ""}
    data = {"provider": "auto", "model": ""}
    if KEYS_FILE.exists():
        try:
            loaded = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data["provider"] = loaded.get("provider", "auto")
                data["model"] = loaded.get("model", "")
        except Exception:
            pass
    data["openai"] = SECRETS.get_secret("OPENAI_API_KEY", "")
    data["groq"] = SECRETS.get_secret("GROQ_API_KEY", "")
    data["openrouter"] = SECRETS.get_secret("OPENROUTER_API_KEY", "")
    return {**defaults, **data}

def _save_keys(data: dict):
    try:
        safe_data = {
            "provider": data.get("provider", "auto"),
            "model": data.get("model", ""),
        }
        KEYS_FILE.write_text(json.dumps(safe_data, indent=2), encoding="utf-8")
    except Exception:
        pass


# ----------------------------------------------------------------------------
# History
# ----------------------------------------------------------------------------

def _load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_history(conversations: list):
    try:
        HISTORY_FILE.write_text(json.dumps(conversations, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Context gathering — what AI knows about user
# ----------------------------------------------------------------------------

def _gather_context() -> dict:
    """Pull all relevant data from local APIs to feed AI."""
    ctx = {}
    from bot.config import get_hub_url
    base = get_hub_url()

    def _fetch(path, timeout=3):
        try:
            return _http_client.get(base + path, timeout=timeout)
        except Exception:
            pass
        return None

    # Seller status & profile
    status   = _fetch("/api/seller/status")
    overview = _fetch("/api/seller/overview")
    balance  = _fetch("/api/seller/balance/full")

    ctx["connected"] = bool(status and (status.get("has_credentials") or status.get("connected")))
    if overview:
        ctx["seller"] = {
            "username": overview.get("username"),
            "id":       overview.get("id") or overview.get("user_id"),
            "rating":   overview.get("rating", 0),
            "reviews":  overview.get("reviews_count", 0),
        }
    if balance:
        ctx["balance"] = {
            "rub":       balance.get("available_rub"),
            "usd":       balance.get("available_usd"),
            "eur":       balance.get("available_eur"),
            "available": balance.get("available"),
        }

    # Trading
    lots   = _fetch("/api/seller/lots")
    orders = _fetch("/api/seller/orders")
    sales  = _fetch("/api/seller/sales")

    lots_list   = (lots and lots.get("lots"))     or lots   or []
    orders_list = (orders and orders.get("orders")) or orders or []
    sales_list  = (sales and sales.get("sales"))   or sales  or []

    ctx["counts"] = {
        "lots":   len(lots_list) if isinstance(lots_list, list) else 0,
        "orders": len(orders_list) if isinstance(orders_list, list) else 0,
        "sales":  len(sales_list) if isinstance(sales_list, list) else 0,
    }

    # Plugins
    plugins = _fetch("/api/plugins")
    plugins_list = (plugins and plugins.get("plugins")) or plugins or []
    if isinstance(plugins_list, list):
        ctx["plugins"] = [
            {
                "name":    p.get("name"),
                "status":  p.get("status"),
                "enabled": p.get("enabled"),
                "version": p.get("version"),
            }
            for p in plugins_list[:20]
        ]

    # Market alerts (recent)
    alerts = _fetch("/api/alerts")
    alerts_list = (alerts and alerts.get("alerts")) or alerts or []
    if isinstance(alerts_list, list):
        ctx["recent_alerts"] = [
            {"level": a.get("severity") or a.get("level"), "msg": a.get("message") or a.get("title")}
            for a in alerts_list[:5]
        ]

    # Margin overview
    margin = _fetch("/api/margin/overview")
    if margin:
        ctx["margin"] = margin

    return ctx


# ----------------------------------------------------------------------------
# System prompt
# ----------------------------------------------------------------------------

SYSTEM_PROMPT = """Ты — встроенный AI ассистент в приложении FunPay Hub.
FunPay Hub — это desktop приложение для автоматизации торговли на FunPay.com.

Твоя роль:
- Помогать пользователю с настройкой и использованием приложения
- Давать конкретные советы по торговле основываясь на его данных
- Объяснять как работают разделы (Лоты, Автоответы, Автовыдача, Плагины и т.д.)
- Предлагать оптимизации цен, плагины, автоматизации

Стиль ответов:
- Кратко и по делу. Без воды.
- На русском языке (если пользователь не пишет на другом).
- Используй разметку Markdown: списки, жирный, код.
- Если нужны данные которых у тебя нет — попроси пользователя открыть нужный раздел.

Если пользователь не подключил аккаунт FunPay — посоветуй зайти в Профиль и подключить golden_key.
"""


KB_FAQ = {
    "автоответ": "Автоответы настраиваются в **Automation → Автоответы**. Создай шаблоны (с переменными `{{buyer_name}}`, `{{order_id}}`), затем правила (триггер → шаблон). Работает 4 типа триггеров: new_chat, review_received, keyword, manual.",
    "автовыдач": "Автовыдача в **Automation → Автовыдача**. Включи переключатель, добавь привязку *Лот ID → файл со стоком*. После каждой оплаты товар уходит автоматически из этого файла.",
    "golden_key": "Открой funpay.com → F12 → Application → Cookies → funpay.com → скопируй значение `golden_key` → вставь в **Profile → Профиль**.",
    "плагин":     "Плагины в **System → Плагины**. Можно включать/выключать/перезапускать. Настройки каждого плагина — кнопка ⚙ рядом с плагином.",
    "бэкап":      "Создать бэкап: `Ctrl+K` → 'бэкап' → Enter. Или зайди в **System → Бэкапы**. Бэкапы сохраняются локально.",
    "тема":       "Кастомизация в **Settings (Внешний вид)**: 10 цветов + свой HEX, 6 фонов + загрузка своих картинок и видео до 100MB, прозрачность, свечение, скругление, скорость анимаций, кастомные звуки.",
    "hotkey":     "Главные хоткеи: `Ctrl+K` поиск, `Ctrl+1..5` навигация, `Ctrl+,` настройки, `Ctrl+/` помощь, `Ctrl+B` свернуть sidebar.",
    "поиск":      "Жми `Ctrl+K` в любом месте — откроется поиск по 27 страницам и быстрым действиям.",
    "ai":         "Это и есть AI ассистент 🙂. Также есть **Market → AI Советник** для рекомендаций по ценам и оптимизации лотов.",
    "конкурент":  "В **Market → Конкуренты** можно отслеживать конкретных продавцов. Кнопка 'Следить' добавит в список — при изменениях их цен придёт алерт.",
    "ниш":        "**Market → Ниши** показывает Score по категориям. Чем выше Score — тем выгоднее зайти в эту нишу.",
    "автоподн":   "Скоро будет плагин AutoBump для автоподнятия лотов (см. **System → Плагины**).",
}

def _kb_lookup(question: str) -> str:
    """Local knowledge base — no internet needed."""
    q = question.lower()
    for key, answer in KB_FAQ.items():
        if key in q:
            return answer
    return None


# ----------------------------------------------------------------------------
# Provider calls
# ----------------------------------------------------------------------------

def _call_openai(messages, api_key, model=None) -> str:
    model = model or "gpt-4o-mini"
    try:
        result = _http_client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":      model,
                "messages":   messages,
                "temperature": 0.5,
                "max_tokens":  800,
            },
            timeout=30,
        )
        return result["choices"][0]["message"]["content"]
    except HTTPClientError as e:
        return f"⚠️ OpenAI error: HTTP {e.status_code} — {e.body[:200] if e.body else str(e)}"
    except Exception as e:
        return f"⚠️ OpenAI failed: {e}"


def _call_groq(messages, api_key, model=None) -> str:
    model = model or "llama-3.3-70b-versatile"
    try:
        result = _http_client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":      model,
                "messages":   messages,
                "temperature": 0.5,
                "max_tokens":  800,
            },
            timeout=30,
        )
        return result["choices"][0]["message"]["content"]
    except HTTPClientError as e:
        return f"⚠️ Groq error: HTTP {e.status_code} — {e.body[:200] if e.body else str(e)}"
    except Exception as e:
        return f"⚠️ Groq failed: {e}"


# Fast-fail client for OpenRouter free-model fallback (retry once, then move to next model)
_or_client = HTTPClient(max_retries=1)

def _call_openrouter(messages, api_key, model=None) -> str:
    """OpenRouter with auto-fallback through multiple free models.
    If specified model is rate-limited, tries others in order."""

    # Priority list of free models - tries each if previous fails
    # Verified working free models as of late 2024/2025
    # Order = priority (best/fastest first)
    FREE_MODELS = [
        "deepseek/deepseek-chat-v3.1:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "mistralai/mistral-small-3.2-24b-instruct:free",
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "openchat/openchat-7b:free",
        "qwen/qwen-2-7b-instruct:free",
    ]

    # If user specified a model, try it first
    models_to_try = []
    if model and model.strip():
        models_to_try.append(model.strip())
    models_to_try.extend([m for m in FREE_MODELS if m != model])

    last_error = None

    for try_model in models_to_try:
        try:
            result = _or_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json",
                    "HTTP-Referer":  "http://funpayhub.local",
                    "X-Title":       "FunPay Hub",
                },
                json={
                    "model":       try_model,
                    "messages":    messages,
                    "temperature": 0.5,
                    "max_tokens":  800,
                },
                timeout=30,
            )

            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"]

            # No choices - try next model
            last_error = f"{try_model}: no choices"
            continue

        except HTTPClientError as e:
            last_error = f"{try_model}: HTTP {e.status_code}" if e.status_code else str(e)
            continue
        except Exception as e:
            last_error = f"{try_model}: {e}"
            continue

    # All models failed
    return f"⚠️ Все бесплатные модели OpenRouter сейчас перегружены. Попробуй через минуту. Последняя ошибка: {last_error}"

@assistant_bp.route("/api/assistant/keys", methods=["GET"])
def get_keys():
    k = _load_keys()
    return jsonify({
        "openai_set":     bool(k.get("openai")),
        "groq_set":       bool(k.get("groq")),
        "openrouter_set": bool(k.get("openrouter")),
        "provider":       k.get("provider", "auto"),
        "model":          k.get("model", ""),
    })


@assistant_bp.route("/api/assistant/keys", methods=["POST"])
def set_keys():
    body = request.json or {}
    k = _load_keys()
    if "openai" in body:
        k["openai"] = body["openai"]
        SECRETS.set_secret("OPENAI_API_KEY", body["openai"])
    if "groq" in body:
        k["groq"] = body["groq"]
        SECRETS.set_secret("GROQ_API_KEY", body["groq"])
    if "openrouter" in body:
        k["openrouter"] = body["openrouter"]
        SECRETS.set_secret("OPENROUTER_API_KEY", body["openrouter"])
    if "provider" in body:   k["provider"]   = body["provider"]
    if "model" in body:      k["model"]      = body["model"]
    _save_keys(k)
    return jsonify({"ok": True})


@assistant_bp.route("/api/assistant/history", methods=["GET"])
def get_history():
    return jsonify({"conversations": _load_history()})


@assistant_bp.route("/api/assistant/history", methods=["DELETE"])
def clear_history():
    _save_history([])
    return jsonify({"ok": True})


@assistant_bp.route("/api/assistant/conversation/<conv_id>", methods=["DELETE"])
def delete_conv(conv_id):
    convs = _load_history()
    convs = [c for c in convs if c.get("id") != conv_id]
    _save_history(convs)
    return jsonify({"ok": True})


@assistant_bp.route("/api/assistant/chat", methods=["POST"])
def chat():
    body = request.json or {}
    user_message = (body.get("message") or "").strip()
    conv_id      = body.get("conversation_id")
    use_context  = body.get("with_context", True)

    if not user_message:
        return jsonify({"ok": False, "error": "empty message"}), 400

    # Load conversation
    convs = _load_history()
    conv = None
    if conv_id:
        for c in convs:
            if c.get("id") == conv_id:
                conv = c
                break

    if conv is None:
        # New conversation
        import uuid
        conv = {
            "id":         str(uuid.uuid4())[:8],
            "title":      user_message[:50],
            "created_at": int(time.time()),
            "messages":   [],
        }
        convs.insert(0, conv)

    # Build messages for AI
    keys = _load_keys()
    provider = keys.get("provider", "auto")

    # Context block (only on first message of conversation)
    context_block = ""
    if use_context and len(conv["messages"]) == 0:
        ctx = _gather_context()
        if ctx:
            context_block = "\n\n[Контекст пользователя]\n" + json.dumps(ctx, ensure_ascii=False, indent=2)

    messages = [{"role": "system", "content": SYSTEM_PROMPT + context_block}]
    for m in conv["messages"]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_message})

    # Decide provider
    reply = None
    used  = "none"

    # Try in order: openai -> groq -> kb
    order = []
    if provider == "openai" and keys.get("openai"):
        order = ["openai"]
    elif provider == "groq" and keys.get("groq"):
        order = ["groq"]
    elif provider == "openrouter" and keys.get("openrouter"):
        order = ["openrouter"]
    else:
        # auto: try openrouter first (works from RU), then openai, then groq
        if keys.get("openrouter"): order.append("openrouter")
        if keys.get("openai"):     order.append("openai")
        if keys.get("groq"):       order.append("groq")
        order.append("kb")

    for p in order:
        if p == "openai":
            reply = _call_openai(messages, keys["openai"], keys.get("model") or None)
            if reply and not reply.startswith("⚠️"):
                used = "openai"
                break
        elif p == "groq":
            reply = _call_groq(messages, keys["groq"], keys.get("model") or None)
            if reply and not reply.startswith("⚠️"):
                used = "groq"
                break
        elif p == "openrouter":
            reply = _call_openrouter(messages, keys["openrouter"], keys.get("model") or None)
            if reply and not reply.startswith("⚠️"):
                used = "openrouter"
                break
        elif p == "kb":
            kb = _kb_lookup(user_message)
            if kb:
                reply = kb + "\n\n*(ответ из встроенной базы знаний — для умных ответов добавь OpenAI или Groq API ключ в Settings)*"
            else:
                reply = ("Я могу отвечать на вопросы о приложении, но для более умных ответов "
                         "нужен API ключ. Зайди в **Settings → AI** и добавь ключ от:\n\n"
                         "- **OpenAI** (платный, лучшее качество): platform.openai.com\n"
                         "- **Groq** (бесплатно с лимитом): console.groq.com\n\n"
                         "Или попробуй задать вопрос про настройки: автоответы, плагины, golden_key, бэкап.")
            used = "kb"
            break

    # Save to history
    conv["messages"].append({"role": "user",      "content": user_message, "ts": int(time.time())})
    conv["messages"].append({"role": "assistant", "content": reply,        "ts": int(time.time()), "provider": used})
    conv["updated_at"] = int(time.time())
    # Limit history to 50 conversations
    convs = convs[:50]
    _save_history(convs)

    return jsonify({
        "ok":              True,
        "conversation_id": conv["id"],
        "reply":           reply,
        "provider":        used,
    })

@assistant_bp.route("/api/assistant/test")
def test_provider():
    """Quick test which OpenRouter free models actually respond right now."""
    keys = _load_keys()
    if not keys.get("openrouter"):
        return jsonify({"ok": False, "error": "no openrouter key"}), 400

    test_models = [
        "deepseek/deepseek-chat-v3.1:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-small-3.2-24b-instruct:free",
    ]

    results = []
    for m in test_models:
        try:
            _http_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {keys['openrouter']}",
                    "Content-Type":  "application/json",
                    "HTTP-Referer":  "http://funpayhub.local",
                    "X-Title":       "FunPay Hub",
                },
                json={
                    "model":      m,
                    "messages":   [{"role":"user","content":"hi"}],
                    "max_tokens": 10,
                },
                timeout=15,
            )
            results.append({"model": m, "status": 200, "ok": True})
        except HTTPClientError as e:
            results.append({"model": m, "status": e.status_code or "error", "ok": False, "err": str(e.last_error)})
        except Exception as e:
            results.append({"model": m, "status": "error", "ok": False, "err": str(e)})

    working = [r for r in results if r["ok"]]
    return jsonify({"ok": True, "working_count": len(working), "results": results})
