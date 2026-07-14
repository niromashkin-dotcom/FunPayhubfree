from runtime.database.database import SessionLocal
from runtime.database.repositories import OrderRepository
from runtime.database.models import OrderStatus
import time

class OrderService:
    """Главный объект системы. Управляет жизненным циклом заказа."""
    
    def __init__(self, event_bus, delivery_service, finance_service, chat_service):
        self.event_bus = event_bus
        self.delivery_service = delivery_service
        self.finance_service = finance_service
        self.chat_service = chat_service

    def create_order(self, order_id: str, buyer: str, lot_name: str):
        with SessionLocal() as db:
            repo = OrderRepository(db)
            return repo.create_order(order_id, buyer, lot_name)

    def process_payment(self, order_id: str, amount: float):
        """Обработка оплаты: смена статуса, запись в Ledger, вызов доставки."""
        with SessionLocal() as db:
            repo = OrderRepository(db)
            order = repo.get_order(order_id)
            if order and order.status != OrderStatus.NEW.value:
                # Idempotency check: already processed
                return
            order = repo.update_status(order_id, OrderStatus.PAID)
            
        # Запись в Ledger
        self.finance_service.record_sale(order_id, amount)
        
        # Вызов автовыдачи
        self.delivery_service.deliver_order(order_id)
        
    def complete_order(self, order_id: str, price: float, cost: float):
        with SessionLocal() as db:
            repo = OrderRepository(db)
            repo.update_status(order_id, OrderStatus.COMPLETED)
            
        self.finance_service.calculate_and_record_profit(order_id, price, cost)
        
    def refund_order(self, order_id: str):
        with SessionLocal() as db:
            repo = OrderRepository(db)
            repo.update_status(order_id, OrderStatus.REFUNDED)
        self.event_bus.emit("order_refunded", {"order_id": order_id})
