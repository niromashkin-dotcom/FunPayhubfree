# runtime/runtime_log.py
import time
from typing import List, Dict, Any, Optional
from enum import Enum
from collections import deque


class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class RuntimeLogEntry:
    def __init__(self, level: LogLevel, source: str, message: str):
        self.timestamp = time.time()
        self.level = level
        self.source = source
        self.message = message
        self.formatted_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> dict:
        return {
            "time": self.formatted_time,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "source": self.source,
            "message": self.message
        }
    
    def __str__(self) -> str:
        return f"[{self.formatted_time}] [{self.level.value}] [{self.source}] {self.message}"


class RuntimeLog:
    MAX_LOG_ENTRIES = 1000
    
    def __init__(self, max_entries: int = MAX_LOG_ENTRIES):
        self._max_entries = max_entries
        self._entries: deque = deque(maxlen=max_entries)
    
    def add(self, level: LogLevel, source: str, message: str) -> RuntimeLogEntry:
        entry = RuntimeLogEntry(level, source, message)
        self._entries.append(entry)
        return entry
    
    def info(self, source: str, message: str) -> RuntimeLogEntry:
        return self.add(LogLevel.INFO, source, message)
    
    def warning(self, source: str, message: str) -> RuntimeLogEntry:
        return self.add(LogLevel.WARNING, source, message)
    
    def error(self, source: str, message: str) -> RuntimeLogEntry:
        return self.add(LogLevel.ERROR, source, message)
    
    def debug(self, source: str, message: str) -> RuntimeLogEntry:
        return self.add(LogLevel.DEBUG, source, message)
    
    def get_entries(self, limit: int = None, level: LogLevel = None) -> List[dict]:
        entries = list(self._entries)
        if level:
            entries = [e for e in entries if e.level == level]
        if limit:
            entries = entries[-limit:]
        return [e.to_dict() for e in entries]
    
    def get_all(self) -> List[dict]:
        return self.get_entries()
    
    def get_last(self, count: int = 10) -> List[dict]:
        return self.get_entries(limit=count)
    
    def clear(self) -> None:
        self._entries.clear()
        self.info("RuntimeLog", "Лог очищен")
    
    def count(self) -> int:
        return len(self._entries)
    
    def get_by_source(self, source: str, limit: int = None) -> List[dict]:
        entries = [e for e in self._entries if e.source == source]
        if limit:
            entries = entries[-limit:]
        return [e.to_dict() for e in entries]