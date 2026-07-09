# runtime/websocket/event_serializer.py
import json
from runtime.event_types import Event

def serialize_event(event: Event) -> str:
    return json.dumps({
        "type": "plugin_event",
        "timestamp": event.timestamp,
        "plugin": event.plugin,
        "action": event.action.value if hasattr(event.action, 'value') else event.action,
        "result": event.result.value if hasattr(event.result, 'value') else event.result,
        "severity": event.severity.value if hasattr(event.severity, 'value') else event.severity,
        "state": event.state,
        "source": event.source.value if hasattr(event.source, 'value') else event.source,
        "message": event.message,
        "correlation_id": event.correlation_id,
        "event_id": event.event_id
    })