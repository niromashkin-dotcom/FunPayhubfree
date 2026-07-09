import os
import json
from typing import Dict, List, Optional
from runtime.http_client import HTTPClient

class SupplierRegistry:
    """Единый источник истины для всех поставщиков."""
    
    SUPPLIERS = {
        "gorgonaboosts": {
            "name": "Gorgona Boosts",
            "url": "https://gorgonaboosts.com/api/",
            "api_key_env": "GORGONA_API_KEY",
            "marker": "[GB#",
            "enabled": True,
            "retry_count": 3
        },
        "looksmm": {
            "name": "LookSMM",
            "url": "https://looksmm.com/api/",
            "api_key_env": "LOOKSMM_API_KEY",
            "marker": "[LS#",
            "enabled": True,
            "retry_count": 3
        },
        "freekassa": {
            "name": "FreeKassa",
            "url": "https://freekassa.com/api/",
            "merchant_id_env": "FREEKASSA_MERCHANT_ID",
            "marker": "[FK#",
            "enabled": True,
            "retry_count": 3
        },
        "holdboost": {
            "name": "HoldBoost",
            "url": "https://holdboost.com/api/",
            "api_key_env": "HOLDBOOST_API_KEY",
            "marker": "[HB#",
            "enabled": True,
            "retry_count": 3
        },
        "stars": {
            "name": "Telegram Stars (Fragment)",
            "url": "https://fragment.com/api",
            "wallet_seed_env": "FRAGMENT_WALLET_SEED",
            "marker": "[ST#",
            "enabled": False,  # включить когда FRAGMENT_WALLET_SEED будет в .env
            "retry_count": 5
        },
        "shopclaude": {
            "name": "ShopClaude",
            "url": None,  # TODO: найти поставщика AI-подписок
            "marker": "[SC#",
            "enabled": False,
            "retry_count": 0
        }
    }
    
    @classmethod
    def get_all_suppliers(cls) -> Dict:
        """Возвращает все поставщики."""
        return cls.SUPPLIERS
    
    @classmethod
    def get_supplier(cls, name: str) -> Optional[Dict]:
        """Получить конфиг поставщика по имени."""
        return cls.SUPPLIERS.get(name)
    
    @classmethod
    def get_enabled_suppliers(cls) -> List[str]:
        """Список включённых поставщиков."""
        return [name for name, cfg in cls.SUPPLIERS.items() if cfg.get("enabled")]
    
    @classmethod
    def get_api_key(cls, supplier_name: str) -> Optional[str]:
        """Получить API-ключ из окружения."""
        supplier = cls.get_supplier(supplier_name)
        if not supplier:
            return None
        
        # Пробуем разные варианты ключей
        env_key = supplier.get("api_key_env")
        if env_key:
            return os.getenv(env_key)
        
        merchant_id_env = supplier.get("merchant_id_env")
        if merchant_id_env:
            return os.getenv(merchant_id_env)
        
        wallet_seed_env = supplier.get("wallet_seed_env")
        if wallet_seed_env:
            return os.getenv(wallet_seed_env)
        
        return None
    
    @classmethod
    def is_enabled(cls, supplier_name: str) -> bool:
        """Проверить включён ли поставщик (и есть ли API-ключ)."""
        supplier = cls.get_supplier(supplier_name)
        if not supplier or not supplier.get("enabled"):
            return False
        
        # Если нет конфига для ключа (например, shopclaude.url == None) — отключен
        if supplier.get("url") is None:
            return False
        
        # Проверить наличие API-ключа
        return cls.get_api_key(supplier_name) is not None
    
    @classmethod
    def get_marker(cls, supplier_name: str) -> Optional[str]:
        """Получить маркер заказа (например [GB#)."""
        supplier = cls.get_supplier(supplier_name)
        return supplier.get("marker") if supplier else None