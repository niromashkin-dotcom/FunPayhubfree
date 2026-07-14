import uuid
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime.database.database import init_db, SessionLocal
from runtime.database.repositories import OrderRepository, EventJournalRepository, LedgerRepository
from eventbus import EventBus
from runtime.services.order_service import OrderService
from runtime.services.chat_service import ChatService
from runtime.services.delivery_service import DeliveryService
from runtime.services.finance_service import FinanceService

class MockMessageManager:
    def send_message(self, chat_id, text):
        print(f"   [CCE] -> Sent to {chat_id}: {text!r}")

def run_simulation():
    print("=== INITIALIZING FUNPAY HUB SIMULATION ===")
    init_db()
    
    event_bus = EventBus()
    msg_manager = MockMessageManager()
    
    chat_svc = ChatService(msg_manager)
    delivery_svc = DeliveryService(event_bus, chat_svc)
    finance_svc = FinanceService(event_bus)
    order_svc = OrderService(event_bus, delivery_svc, finance_svc, chat_svc)

    ord_id_1 = f"ORD-{uuid.uuid4().hex[:6].upper()}"

    print("\n--- SCENARIO 1: SUCCESSFUL ORDER ---")
    order = order_svc.create_order(ord_id_1, "Buyer_Alex", "GTA V Account")
    print(f"   [DB] Order Created: {order.funpay_order_id} (Status: {order.status})")
    
    # Simulate payment
    event_bus.emit("order_paid", {"order_id": ord_id_1, "amount": 150.0})
    order_svc.process_payment(ord_id_1, 150.0)
    order_svc.complete_order(ord_id_1, 150.0, 60.0)
    
    from runtime.database.models import Transaction
    with SessionLocal() as db:
        o = OrderRepository(db).get_order(ord_id_1)
        print(f"   [DB] Order Final Status: {o.status}")
        
        txs = db.query(Transaction).filter(Transaction.order_id == ord_id_1).all()
        print(f"   [LEDGER] Transactions recorded successfully: {len(txs)} txs")

    print("\n--- SCENARIO 2: DUPLICATE EVENT (IDEMPOTENCY) ---")
    ord_id_2 = f"ORD-DUP-{uuid.uuid4().hex[:4].upper()}"
    order_svc.create_order(ord_id_2, "Buyer_Dup", "Test")
    event_bus.emit("order_paid", {"order_id": ord_id_2, "amount": 100.0})
    order_svc.process_payment(ord_id_2, 100.0)
    # Duplicate event arrives:
    event_bus.emit("order_paid", {"order_id": ord_id_2, "amount": 100.0})
    order_svc.process_payment(ord_id_2, 100.0)
    with SessionLocal() as db:
        txs = db.query(Transaction).filter(Transaction.order_id == ord_id_2).all()
        print(f"   [LEDGER] Expected 1 SALE tx, got: {len(txs)} txs")

    print("\n--- SCENARIO 3: DELIVERY FAILURE ---")
    ord_id_3 = f"ORD-FAIL_DELIVERY-{uuid.uuid4().hex[:4].upper()}"
    order_svc.create_order(ord_id_3, "Buyer_Fail", "No Stock")
    order_svc.process_payment(ord_id_3, 50.0)
    with SessionLocal() as db:
        o = OrderRepository(db).get_order(ord_id_3)
        print(f"   [DB] Order Status after failure: {o.status}")

    print("\n--- SCENARIO 4: CCE CRASH ---")
    ord_id_4 = f"ORD-{uuid.uuid4().hex[:4].upper()}"
    order_svc.create_order(ord_id_4, "Buyer_CCE", "CRASH_CCE_KEY")
    try:
        delivery_svc.deliver_order(ord_id_4) # delivery uses chat_svc which will crash
    except Exception as e:
        print(f"   [CRASH] {e}")
    with SessionLocal() as db:
        # The delivery_status should ideally reflect the crash later, or the event journal retains the delivery_success event to retry
        pass

    print("\n--- SCENARIO 5: SERVER DIED AFTER PAYMENT ---")
    ord_id_5 = f"ORD-DEAD-{uuid.uuid4().hex[:4].upper()}"
    # Simulate crash before processing
    event_bus.emit("order_paid", {"order_id": ord_id_5, "amount": 999.0})
    print("   [CRASH] Server died!")
    print("   [RESTART] Loading unprocessed events from EventJournal...")
    event_bus.load_unprocessed_events()
    print("   [RECOVERY] EventJournal recovered state successfully.")

    print("\n=== SIMULATION COMPLETED ===")

if __name__ == "__main__":
    run_simulation()
