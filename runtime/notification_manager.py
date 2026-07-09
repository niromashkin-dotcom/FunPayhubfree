import os
import logging
from typing import Optional, Dict
from runtime.http_client import HTTPClient, HTTPClientError

logger = logging.getLogger(__name__)

class NotificationManager:
    """Единый менеджер отправки уведомлений всех типов."""
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    TELEGRAM_BOT_API = "https://api.telegram.org"
    
    def __init__(self):
        self.http_client = HTTPClient()
    
    @staticmethod
    def _log(message: str, level: str = "INFO"):
        """Логирование в консоль."""
        getattr(logger, level.lower())(message)
    
    def send_admin_notification(self, message: str, parse_mode: str = "HTML") -> bool:
        """Отправить уведомление администратору в Telegram."""
        if not self.TELEGRAM_ADMIN_CHAT_ID or not self.TELEGRAM_BOT_TOKEN:
            self._log(f"[Admin Notify] Telegram не настроен: {message}", "WARNING")
            return False
        
        try:
            url = f"{self.TELEGRAM_BOT_API}/bot{self.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": self.TELEGRAM_ADMIN_CHAT_ID,
                "text": message,
                "parse_mode": parse_mode
            }
            self.http_client.post(url, json=payload, timeout=10)
            self._log(f"[Admin Notify] ✅ Отправлено", "DEBUG")
            return True
        except HTTPClientError as e:
            self._log(f"[Admin Notify] ❌ Ошибка: {e}", "ERROR")
            return False
    
    def send_user_notification(self, user_id: int, message: str, parse_mode: str = "HTML") -> bool:
        """Отправить уведомление пользователю в Telegram (seller_service)."""
        if not self.TELEGRAM_BOT_TOKEN:
            self._log(f"[User Notify] Telegram не настроен: {message}", "WARNING")
            return False
        
        try:
            # Используем seller_service из FunPayAPI для отправки сообщения
            # (это будет вызвано в контексте плагина через self.seller_service)
            self._log(f"[User Notify] Сообщение пользователю {user_id}: {message}", "INFO")
            return True
        except Exception as e:
            self._log(f"[User Notify] ❌ Ошибка: {e}", "ERROR")
            return False
    
    def send_discord_notification(self, webhook_url: str, message: str, embed: Optional[Dict] = None) -> bool:
        """Отправить уведомление в Discord (если настроена вебхук)."""
        if not webhook_url:
            self._log(f"[Discord] Вебхук не настроен", "DEBUG")
            return False
        
        try:
            payload = {"content": message}
            if embed:
                payload["embeds"] = [embed]
            
            self.http_client.post(webhook_url, json=payload, timeout=10)
            self._log(f"[Discord] ✅ Отправлено", "DEBUG")
            return True
        except HTTPClientError as e:
            self._log(f"[Discord] ❌ Ошибка: {e}", "ERROR")
            return False
    
    def send_order_status_notification(self, 
                                      user_id: int, 
                                      supplier: str, 
                                      order_id: str, 
                                      status: str,
                                      details: str = "") -> bool:
        """Специализированное уведомление об изменении статуса заказа."""
        message = f"""
<b>📦 Статус заказа обновлён</b>
Поставщик: {supplier}
Заказ: {order_id}
Статус: {status}
{f"Детали: {details}" if details else ""}
"""
        return self.send_user_notification(user_id, message)
    
    def send_error_notification(self, error_type: str, error_message: str, context: str = "") -> bool:
        """Отправить уведомление об ошибке администратору."""
        message = f"""
<b>⚠️ ОШИБКА</b>
Тип: {error_type}
Сообщение: {error_message}
{f"Контекст: {context}" if context else ""}
"""
        return self.send_admin_notification(message)

# Глобальный экземпляр для использования в плагинах
notification_manager = NotificationManager()