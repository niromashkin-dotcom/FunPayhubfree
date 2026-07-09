# runtime/event_types.py
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class EventAction(Enum):
    ENABLE = "enable"
    DISABLE = "disable"
    RESTART = "restart"
    RELOAD_CONFIG = "reload_config"
    REGISTER = "register"
    UNREGISTER = "unregister"
    SHUTDOWN = "shutdown"
    CLEAR_LOGS = "clear_logs"


class EventResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ALREADY_ACTIVE = "already_active"
    NOT_FOUND = "not_found"


class EventSource(Enum):
    RUNTIME_CONTROLLER = "runtime_controller"
    PLUGIN_MANAGER = "plugin_manager"
    PLUGIN = "plugin"
    CARDINAL = "cardinal"


class EventSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Event:
    action: EventAction
    plugin: str
    result: EventResult
    state: str = None
    source: EventSource = EventSource.RUNTIME_CONTROLLER
    message: str = None
    severity: EventSeverity = EventSeverity.INFO
    correlation_id: str = None
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: f"{int(time.time()*1000)}-{uuid.uuid4().hex[:8]}")

    def __post_init__(self):
        if self.correlation_id is None:
            self.correlation_id = self.event_id
        # Auto severity
        if self.result == EventResult.FAILED or self.result == EventResult.NOT_FOUND:
            self.severity = EventSeverity.ERROR
        elif self.result == EventResult.ALREADY_ACTIVE:
            self.severity = EventSeverity.WARNING

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "action": self.action.value,
            "plugin": self.plugin,
            "result": self.result.value,
            "state": self.state,
            "source": self.source.value,
            "message": self.message,
            "severity": self.severity.value
        }