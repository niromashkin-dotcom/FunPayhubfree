import os
import json
import tempfile
from typing import Optional, Dict, Any

class JsonStorage:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_dir()

    def _ensure_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def save(self, data: Dict[str, Any]) -> bool:
        try:
            tmp_path = self.file_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.file_path)
            return True
        except Exception as e:
            print(f"[StateStorage] Save error: {e}")
            return False

    def load(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return None
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[StateStorage] Load error: {e}")
            return None

    def clear(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        if os.path.exists(self.file_path + ".tmp"):
            os.remove(self.file_path + ".tmp")