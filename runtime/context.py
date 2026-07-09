# runtime/context.py
class AppContext:
    def __init__(self):
        self.runtime_controller = None
        self.event_bus = None
        self.websocket_hub = None
        self.snapshot_builder = None
        self._snapshot = None

    def set_runtime_controller(self, controller):
        self.runtime_controller = controller

    def set_event_bus(self, bus):
        self.event_bus = bus

    def set_websocket_hub(self, hub):
        self.websocket_hub = hub

    def set_snapshot_builder(self, builder):
        self.snapshot_builder = builder

    def update_snapshot(self, snapshot):
        self._snapshot = snapshot

    def get_snapshot(self):
        return self._snapshot

    def get_runtime_controller(self):
        return self.runtime_controller

    def get_event_bus(self):
        return self.event_bus

    def get_websocket_hub(self):
        return self.websocket_hub


_app_context = None

def get_app_context():
    global _app_context
    if _app_context is None:
        _app_context = AppContext()
    return _app_context