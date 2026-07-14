class ChatService:
    """Прокси к MessageManager. CCE нельзя обходить!"""
    
    def __init__(self, message_manager):
        self.message_manager = message_manager

    def send_message(self, chat_id: str, text: str):
        """Единственная разрешенная точка отправки сообщений"""
        self.message_manager.send_message(chat_id, text)

    def get_messages(self, chat_id: str):
        return self.message_manager.get_chat_history(chat_id)

    def reply_review(self, order_id: str, text: str):
        # Логика ответа на отзыв
        pass
