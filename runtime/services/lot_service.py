class LotService:
    """Управление лотами: изменение цен, активация/деактивация"""
    
    def __init__(self, event_bus, funpay_api):
        self.event_bus = event_bus
        self.api = funpay_api

    def get_my_lots(self):
        # вызов API
        pass

    def update_lot_price(self, lot_id: str, new_price: float):
        # вызов API
        pass
        
    def toggle_lot_active(self, lot_id: str, is_active: bool):
        # вызов API
        pass
