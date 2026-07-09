"""
Lot Generator for FunPay Hub
Generates lot variations for AutoSMM and Donate plugins.
"""
import os
import json
import random
import itertools
from pathlib import Path
from typing import List, Dict, Any, Optional


class LotGenerator:
    def __init__(self, seller_service=None):
        self._seller_service = seller_service
        self._services_cache = None
        self._cache_path = Path("data/autosmm/twiboost_services_cache.json")
        self._return_policy = self._load_return_policy()
        self._synonyms = self._load_synonyms()
        self._emojis = self._load_emojis()

    def _load_return_policy(self) -> str:
        policy_path = Path("configs/plugins/templates/return_policy.txt")
        if policy_path.exists():
            try:
                return policy_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return "Возврат в течение 24 часов при проблемах с услугой."

    def _load_synonyms(self) -> dict:
        path = Path("data/synonyms.json")
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("synonyms", {}) if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_emojis(self) -> dict:
        path = Path("data/lot_emojis.json")
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_twiboost_services(self) -> List[Dict[str, Any]]:
        if self._services_cache is not None:
            return self._services_cache
        if not self._cache_path.exists():
            return []
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            self._services_cache = data.get("services", []) if isinstance(data, dict) else []
            return self._services_cache
        except Exception:
            return []

    def _categorize_service(self, service: Dict[str, Any]) -> tuple[str, str]:
        name = (service.get("name") or "").lower()
        category = (service.get("category") or "").lower()
        text = name + " " + category
        platform = "other"
        for key in ["telegram", "vk", "vkontakte", "instagram", "tiktok", "youtube", "twitch", "twitter", "x.com", "kick", "max", "rutube", "discord"]:
            if key in text:
                platform = key
                break
        stype = "other"
        for key in ["подписчик", "follower", "subscriber", "member", "просмотр", "view", "лайк", "like", "реакция", "reaction", "коммент", "comment", "репост", "share", "premium", "звёзд", "stars", "клик", "click", "буст", "boost"]:
            if key in text:
                stype = key
                break
        return platform, stype

    def _mutate_title(self, title: str, emoji_cycle: str) -> str:
        words = title.split()
        if not words:
            return title
        if words[0] in self._emojis.get("emojis_start", []):
            words[0] = emoji_cycle
        elif len(words) > 1 and random.random() < 0.3:
            words[0], words[1] = words[1], words[0]
        syn_map = self._synonyms.get("synonyms", {})
        for i, w in enumerate(words):
            low = w.lower()
            for key, vals in syn_map.items():
                if low == key and vals:
                    words[i] = random.choice(vals)
                    break
        return " ".join(words)

    def generate_lots_for_service(self, service_id: int, base_title: str, quantity: int = 1000, copies: int = 15, max_price: float = 150.0, marker: str = "[AS#") -> List[Dict[str, Any]]:
        service = None
        for s in self._load_twiboost_services():
            if str(s.get("service_id")) == str(service_id):
                service = s
                break
        if not service:
            return []

        platform, stype = self._categorize_service(service)
        svc_name = service.get("name", base_title)
        rate = float(service.get("rate") or 0)
        cost = rate * quantity / 1000 if rate else 40.0
        final_price = round(cost * 1.3, 2)
        if final_price > max_price:
            return []

        platform_names = {
            "telegram": ["Telegram", "TG", "ТЕЛЕГРАМ"],
            "vk": ["ВК", "VK", "ВКонтакте"],
            "instagram": ["Instagram", "INSTAGRAM", "Инста"],
            "tiktok": ["TikTok", "TIKTOK", "ТикТок"],
            "youtube": ["YouTube", "YOUTUBE", "Ютуб"],
            "twitch": ["Twitch", "TWITCH", "Твич"],
            "twitter": ["Twitter", "X", "Твиттер"],
            "discord": ["Discord", "DISCORD"],
        }
        type_names = {
            "подписчик": ["Подписчиков", "ПОДПИСЧИКОВ", "подписчики", "followers"],
            "просмотр": ["Просмотров", "ПРОСМОТРОВ", "просмотры", "views"],
            "лайк": ["Лайков", "ЛАЙКОВ", "лайки", "likes"],
            "реакция": ["Реакций", "РЕАКЦИЙ", "reactions"],
            "коммент": ["Комментариев", "КОММЕНТАРИЕВ", "comments"],
            "репост": ["Репостов", "РЕПОСТОВ", "shares"],
            "premium": ["Premium", "PREMIUM"],
            "звёзд": ["Звёзд", "ЗВЁЗД", "stars"],
            "буст": ["Бустов", "БУСТОВ", "boosts"],
        }
        plats = platform_names.get(platform, [platform.capitalize()])
        types = type_names.get(stype, [stype.capitalize()])
        emojis_start = self._emojis.get("emojis_start", ["🔥", "⭐", "🚀", "💎", "✅", "💫", "✨", "🎯", "⚡", "💥"])
        tails = self._emojis.get("emojis_tail", ["БЫСТРО", "моментально", "ГАРАНТИЯ", "живые", "без списаний", "стабильно", "топ", "PRO", "новинка"])
        templates = self._synonyms.get("title_templates", [
            "{emoji} {quantity} {type} {platform} {tail}",
            "{emoji} {platform} | {quantity} {type} | {tail}",
            "{emoji} {type} {platform} {quantity} штук {tail}",
            "{platform} {quantity} {type} {emoji} {tail}",
        ])

        def make_donor():
            e1 = random.choice(emojis_start)
            plat = random.choice(plats)
            typ = random.choice(types)
            tail = random.choice(tails) if random.random() < 0.5 else ""
            tmpl = random.choice(templates)
            title = tmpl.format(emoji=e1, quantity=quantity, type=typ, platform=plat, tail=tail, marker=marker, service_id=service_id)
            return " ".join(title.split()), e1

        lots = []
        donor_title, first_emoji = make_donor()
        lots.append({
            "title": donor_title,
            "description": self._make_descr(quantity, types[0] if types else stype, plats[0] if plats else platform),
            "price_rub": final_price,
            "amount": 1,
            "marker": f"{marker}{service_id}]",
            "service_id": service_id,
            "service_name": svc_name,
            "quantity": quantity,
            "platform": platform,
            "type": stype,
            "is_donor": True,
        })

        emoji_cycle = itertools.cycle(emojis_start)
        seen = {donor_title}
        attempts = 0
        while len(lots) < copies and attempts < copies * 20:
            attempts += 1
            next(emoji_cycle)
            e1 = next(emoji_cycle)
            plat = random.choice(plats)
            typ = random.choice(types)
            tail = random.choice(tails) if random.random() < 0.5 else ""
            tmpl = random.choice(templates)
            raw = tmpl.format(emoji=e1, quantity=quantity, type=typ, platform=plat, tail=tail, marker=marker, service_id=service_id)
            title = self._mutate_title(" ".join(raw.split()), e1)
            if title in seen:
                continue
            seen.add(title)
            lots.append({
                "title": title,
                "description": self._make_descr(quantity, typ, plat),
                "price_rub": final_price + random.choice([-1, 0, 0, 0, 1]),
                "amount": 1,
                "marker": f"{marker}{service_id}]",
                "service_id": service_id,
                "service_name": svc_name,
                "quantity": quantity,
                "platform": platform,
                "type": stype,
                "is_donor": False,
            })
        return lots

    def _make_descr(self, quantity, typ, plat):
        return (
            f"✅ Вы получаете: {quantity} {typ.lower()} для {plat}\n"
            f"⚡ Время выполнения: 1-24 часа\n"
            f"🎯 Гарантия стабильности\n\n"
            f"{self._return_policy}"
        )

    def generate_discord_boost_lots(self, supplier: str, months: int = 1, copies: int = 15, max_price: float = 150.0) -> List[Dict[str, Any]]:
        marker = "[GB#" if supplier == "gorgona" else "[HB#"
        name = "GorgonaBoosts" if supplier == "gorgona" else "HoldBoost"
        plat = "Discord"
        typ = "Бустов"
        tails = self._emojis.get("emojis_tail", ["БЫСТРО", "моментально", "ГАРАНТИЯ", "стабильно", "топ", "PRO", "новинка", "без списаний"])
        emojis_start = self._emojis.get("emojis_start", ["🔥", "⭐", "🚀", "💎", "✅", "💫", "✨", "🎯", "⚡"])
        templates = self._synonyms.get("title_templates", [
            "{emoji} Discord Boost {months}м | {plat} {tail}",
            "{emoji} {plat} Boost {months} месяц {tail}",
            "{emoji} Буст {plat} на {months}м {tail}",
        ])
        final_price = round((float(months) * 50.0) * 1.3, 2)
        if final_price > max_price:
            return []
        lots = []
        seen = set()
        emoji_cycle = itertools.cycle(emojis_start)
        while len(lots) < copies:
            next(emoji_cycle)
            e1 = next(emoji_cycle)
            tail = random.choice(tails) if random.random() < 0.5 else ""
            tmpl = random.choice(templates)
            raw = tmpl.format(emoji=e1, months=months, plat=plat, tail=tail, marker=marker)
            title = " ".join(raw.split())
            if title in seen:
                continue
            seen.add(title)
            descr = (
                f"✅ Discord Boost на {months} месяц(а)\n"
                f"⚡ Применение: 5-30 минут\n"
                f"🎯 Гарантия стабильности\n\n"
                f"{self._return_policy}"
            )
            lots.append({
                "title": title,
                "description": descr,
                "price_rub": final_price + random.choice([-1, 0, 0, 0, 1]),
                "amount": 1,
                "marker": f"{marker}{months}]",
                "supplier": supplier,
                "months": months,
                "type": "discord_boost",
            })
        return lots

    def generate_kosell_lots(self, products: List[Dict[str, Any]], copies: int = 15, max_price: float = 150.0) -> List[Dict[str, Any]]:
        lots = []
        templates = [
            "🎮 {name} — {hours}ч аренда",
            "🔥 Аренда {name} на {hours} часов",
            "⭐ {name} | {hours}ч | мгновенная выдача",
            "🎯 {hours}ч аренды: {name}",
            "🚀 {name} {hours} часов — доступ сразу",
        ]
        for product in products:
            pid = product.get("id") or product.get("product_id")
            name = product.get("name") or f"Товар #{pid}"
            cost = float(product.get("price") or 50.0)
            for hours in [1, 3, 6, 12, 24, 48, 72, 168]:
                final_price = round(cost * 1.3, 2)
                if final_price > max_price:
                    continue
                seen = set()
                while len([l for l in lots if l.get("product_id") == pid and l.get("hours") == hours]) < copies:
                    tmpl = random.choice(templates)
                    raw = tmpl.format(name=name, hours=hours, marker=f"[KS#{pid}:{hours}]")
                    title = " ".join(raw.split())
                    if title in seen:
                        continue
                    seen.add(title)
                    descr = (
                        f"✅ Аренда: {name}\n"
                        f"⏱ Срок: {hours} часов\n"
                        f"📋 Данные для входа приходят сразу после оплаты\n\n"
                        f"{self._return_policy}"
                    )
                    lots.append({
                        "title": title,
                        "description": descr,
                        "price_rub": final_price + random.choice([-1, 0, 0, 0, 1]),
                        "amount": 1,
                        "marker": f"[KS#{pid}:{hours}]",
                        "product_id": pid,
                        "product_name": name,
                        "hours": hours,
                        "type": "game_rental",
                    })
        return lots

    def generate_all_lots(self, copies: int = 15, max_price: float = 150.0) -> Dict[str, List[Dict[str, Any]]]:
        result = {
            "autosmm": [],
            "donate_gorgona": [],
            "donate_holdboost": [],
            "donate_kosell": [],
        }
        services = self._load_twiboost_services()
        for svc in services:
            sid = svc.get("service_id")
            if sid:
                lots = self.generate_lots_for_service(sid, svc.get("name", ""), copies=copies, max_price=max_price)
                result["autosmm"].extend(lots)

        result["donate_gorgona"] = self.generate_discord_boost_lots("gorgona", months=1, copies=copies, max_price=max_price)
        result["donate_gorgona"].extend(self.generate_discord_boost_lots("gorgona", months=3, copies=copies, max_price=max_price))
        result["donate_holdboost"] = self.generate_discord_boost_lots("holdboost", months=1, copies=copies, max_price=max_price)
        result["donate_holdboost"].extend(self.generate_discord_boost_lots("holdboost", months=3, copies=copies, max_price=max_price))

        kosell_products = self._load_kosell_products()
        if kosell_products:
            result["donate_kosell"] = self.generate_kosell_lots(kosell_products, copies=copies, max_price=max_price)

        return result

    def save_lots(self, lots: List[Dict[str, Any]], plugin: str, supplier: str = "") -> Dict[str, Any]:
        if not self._seller_service:
            return {"ok": False, "error": "seller_service not available"}
        created = 0
        failed = 0
        for lot in lots:
            try:
                title = lot.get("title", "")
                descr = lot.get("description", "")
                price = float(lot.get("price_rub") or 0)
                if not title or not price:
                    failed += 1
                    continue
                result = self._seller_service.create_lot({
                    "title": title,
                    "description": descr,
                    "price": price,
                    "amount": lot.get("amount", 1),
                    "category_id": None,
                })
                if result.get("ok"):
                    created += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        return {"ok": True, "created": created, "failed": failed, "total": len(lots)}
