# runtime/notifications/notification_types.py
from enum import Enum
from dataclasses import dataclass, field
import time
import uuid

class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Notification:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    type: NotificationType = NotificationType.INFO
    title: str = ""
    message: str = ""
    source: str = "system"
    correlation_id: str = None

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "correlation_id": self.correlation_id
        }