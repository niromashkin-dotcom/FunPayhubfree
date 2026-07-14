from runtime.database.database import SessionLocal
from runtime.database.repositories import OrderRepository
from runtime.database.models import OrderStatus

class DeliveryService:
    """Изолированная автовыдача. Вызывается из OrderService."""
    
    def __init__(self, event_bus, chat_service):
        self.event_bus = event_bus
        self.chat_service = chat_service

    def deliver_order(self, order_id: str):
        # 1. Поиск заказа
        with SessionLocal() as db:
            repo = OrderRepository(db)
            order = repo.get_order(order_id)
            if not order:
                self.event_bus.emit("delivery_failed", {"order_id": order_id, "reason": "order_not_found"})
                return

        # 2. Логика выдачи (обращение к поставщику, генерация ключа и т.д.)
        if "FAIL_DELIVERY" in order_id:
            with SessionLocal() as db:
                repo = OrderRepository(db)
                repo.update_status(order_id, OrderStatus.FAILED)
            self.event_bus.emit("delivery_failed", {"order_id": order_id, "reason": "supplier_error"})
            self.chat_service.send_message("admin", f"ALARM: Ошибка поставщика по заказу {order_id}!")
            return

        # В симуляции:
        key = f"SIMULATION-KEY-{order_id}"
        
        # 3. Отправка ключа покупателю строго через ChatService -> CCE
        self.chat_service.send_message(order.buyer_id, f"Ваш товар: {key}\nСпасибо за покупку!")
        
        # 4. Смена статуса
        with SessionLocal() as db:
            repo = OrderRepository(db)
            repo.update_status(order_id, OrderStatus.DELIVERED)
            
        self.event_bus.emit("delivery_success", {"order_id": order_id, "key": key})
