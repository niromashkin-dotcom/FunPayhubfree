# state_api.py
# State API Wrapper Layer v1
# UI и плагины работают ТОЛЬКО через этот слой.
# Cardinal НЕ ЗНАЕТ о StateAPI (инъекция снаружи)

import time
from typing import Any, Dict, List, Optional
from copy import deepcopy

class StateAPI:
    """
    Тонкий слой доступа к данным Cardinal.
    Получает cardinal через dependency injection.
    UI и плагины работают через этот слой.
    """
    
    def __init__(self, cardinal):
        self._cardinal = cardinal
    
    def _get_state(self) -> dict:
        return self._cardinal.get_state()
    
    def _get_lock(self):
        return self._cardinal._state_lock
    
    def get_state(self) -> dict:
        with self._get_lock():
            return deepcopy(self._get_state())
    
    def get_field(self, key: str, default: Any = None) -> Any:
        with self._get_lock():
            return deepcopy(self._get_state().get(key, default))
    
    def get_balance(self) -> float:
        with self._get_lock():
            return float(self._get_state().get("balance", 0.0))
    
    def get_withdrawable(self) -> float:
        with self._get_lock():
            return float(self._get_state().get("withdrawable", 0.0))
    
    def get_lots(self) -> List[dict]:
        with self._get_lock():
            return deepcopy(self._get_state().get("lots", []))
    
    def get_total_lots(self) -> int:
        with self._get_lock():
            return int(self._get_state().get("total_lots", 0))
    
    def get_active_lots(self) -> int:
        with self._get_lock():
            return int(self._get_state().get("active_lots", 0))
    
    def get_profile(self) -> dict:
        with self._get_lock():
            return deepcopy(self._get_state().get("profile", {}))
    
    def get_username(self) -> str:
        with self._get_lock():
            profile = self._get_state().get("profile", {})
            return profile.get("username", "Unknown")
    
    def get_user_id(self) -> Optional[int]:
        with self._get_lock():
            profile = self._get_state().get("profile", {})
            return profile.get("id")
    
    def get_status(self) -> str:
        with self._get_lock():
            return str(self._get_state().get("status", "init"))
    
    def get_last_update(self) -> float:
        with self._get_lock():
            return float(self._get_state().get("last_update", 0.0))
    
    def get_logs(self, limit: int = 50) -> List[str]:
        with self._get_lock():
            logs = self._get_state().get("logs", [])
            return deepcopy(logs[-limit:]) if logs else []
    
    def is_online(self) -> bool:
        with self._get_lock():
            return self._get_state().get("status") == "online"
    
    def to_dict(self) -> dict:
        return self.get_state()