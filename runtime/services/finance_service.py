from runtime.database.database import SessionLocal
from runtime.database.repositories import LedgerRepository
from runtime.database.models import TransactionType

class FinanceService:
    """Управляет Ledger (Финансовым Журналом). Никаких вычислений профита в плагинах!"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus

    def record_sale(self, order_id: str, amount: float):
        """Запись дохода от продажи"""
        with SessionLocal() as db:
            repo = LedgerRepository(db)
            repo.add_transaction(order_id, TransactionType.SALE.value, amount)

    def record_cost(self, order_id: str, cost: float):
        """Запись расходов на поставщика"""
        with SessionLocal() as db:
            repo = LedgerRepository(db)
            repo.add_transaction(order_id, TransactionType.PROVIDER_COST.value, -cost)

    def calculate_and_record_profit(self, order_id: str, price: float, cost: float):
        """Единое место вычисления профита"""
        profit = price - cost
        with SessionLocal() as db:
            repo = LedgerRepository(db)
            repo.add_transaction(order_id, TransactionType.PROFIT.value, profit)
        return profit
