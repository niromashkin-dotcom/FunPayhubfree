# eventbus.py
import threading
from typing import Dict, List, Callable, Any
from collections import defaultdict
import json

class EventBus:
    """Единая шина событий системы с сохранением в EventJournal."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable, priority=0) -> None:
        with self._lock:
            if handler not in self._listeners[event_type]:
                self._listeners[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        with self._lock:
            if event_type in self._listeners and handler in self._listeners[event_type]:
                self._listeners[event_type].remove(handler)

    def _save_event(self, event_type: str, event: Any) -> int:
        from runtime.database.database import SessionLocal
        from runtime.database.repositories import EventJournalRepository
        try:
            with SessionLocal() as db:
                repo = EventJournalRepository(db)
                if hasattr(event, "to_dict"):
                    payload = event.to_dict()
                elif hasattr(event, "__dict__"):
                    payload = event.__dict__
                elif isinstance(event, dict):
                    payload = event
                else:
                    payload = {"data": str(event)}
                journal_entry = repo.log_event(event_type, payload)
                return journal_entry.id
        except Exception as e:
            print(f"[EventBus] Failed to save event to journal: {e}")
            return None

    def _mark_processing(self, journal_id: int):
        from runtime.database.database import SessionLocal
        from runtime.database.repositories import EventJournalRepository
        try:
            with SessionLocal() as db:
                repo = EventJournalRepository(db)
                repo.mark_processing(journal_id)
        except Exception as e:
            pass

    def _mark_processed(self, journal_id: int, failed: bool = False):
        from runtime.database.database import SessionLocal
        from runtime.database.repositories import EventJournalRepository
        try:
            with SessionLocal() as db:
                repo = EventJournalRepository(db)
                if failed:
                    repo.mark_failed(journal_id)
                else:
                    repo.mark_processed(journal_id)
        except Exception as e:
            print(f"[EventBus] Failed to mark event as processed/failed: {e}")

    def emit(self, event_type: str, event: Any) -> None:
        journal_id = self._save_event(event_type, event)
        if journal_id:
            self._mark_processing(journal_id)
        
        with self._lock:
            handlers = self._listeners.get(event_type, []).copy()
            
        has_error = False
        for handler in handlers:
            try:
                handler(event_type, event)
            except Exception as e:
                print(f"[EventBus] Handler error: {e}")
                has_error = True
                
        if journal_id:
            self._mark_processed(journal_id, failed=has_error)

    def publish(self, event_type: str, event: Any) -> None:
        self.emit(event_type, event)
        
    def load_unprocessed_events(self):
        """Метод для запуска после рестарта сервера"""
        from runtime.database.database import SessionLocal
        from runtime.database.repositories import EventJournalRepository
        try:
            with SessionLocal() as db:
                repo = EventJournalRepository(db)
                events = repo.get_unprocessed_events()
                for ev in events:
                    print(f"[EventBus] Recovering unprocessed event: {ev.event_type}")
                    payload = json.loads(ev.payload)
                    with self._lock:
                        handlers = self._listeners.get(ev.event_type, []).copy()
                    for handler in handlers:
                        try:
                            handler(ev.event_type, payload)
                        except Exception as e:
                            print(f"[EventBus] Handler error during recovery: {e}")
                    repo.mark_processed(ev.id)
        except Exception as e:
            print(f"[EventBus] Failed to load unprocessed events: {e}")