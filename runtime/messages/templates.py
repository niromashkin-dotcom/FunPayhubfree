from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MessageTemplate:
    key: str
    text: str
    requires_db: bool = False
    requires_api: bool = False
    parse_mode: str = "HTML"
    max_length: int = 4096


ORDER_TEMPLATES: Dict[str, MessageTemplate] = {
    "new_order": MessageTemplate(
        key="new_order",
        text=(
            "🎉 Спасибо за покупку!\n\n"
            "Ваш заказ успешно получен.\n"
            "📦 Название: {order_title}\n"
            "🆔 №{order_id}\n\n"
            "Уже начинаем обработку.\n"
            "Обычно выполнение занимает около {eta} минут.\n"
            "Если понадобятся дополнительные данные — мы сразу напишем вам.\n\n"
            "Спасибо за доверие ❤️"
        ),
        requires_db=True,
    ),
    "greeting": MessageTemplate(
        key="greeting",
        text=(
            "👋 Привет!\n\n"
            "Спасибо за заказ 🙏\n"
            "📦 {order_title}\n"
            "💰 {price} ₽\n\n"
            "Для выполнения заказа нужна ссылка.\n"
            "Подойдут:\n"
            "✅ профиль\n"
            "✅ канал\n"
            "✅ пост\n"
            "✅ видео\n\n"
            "Пожалуйста, отправьте ссылку. После проверки мы сразу начнем выполнение."
        ),
        requires_db=True,
    ),
    "link_request": MessageTemplate(
        key="link_request",
        text=(
            "Для выполнения заказа нужна ссылка.\n\n"
            "Подойдут:\n"
            "✅ профиль\n"
            "✅ канал\n"
            "✅ пост\n"
            "✅ видео\n\n"
            "Пожалуйста, отправьте ссылку."
        ),
        requires_db=False,
    ),
    "link_received": MessageTemplate(
        key="link_received",
        text=(
            "Мы получили {link}\n\n"
            "Проверьте, пожалуйста:\n"
            "✅ Всё верно\n"
            "✏️ Отправить другую ссылку\n\n"
            "Напишите «да», если всё верно.\n"
            "Если ошибка — пришлите верную ссылку."
        ),
        requires_db=True,
    ),
    "confirm": MessageTemplate(
        key="confirm",
        text=(
            "Отлично!\n\n"
            "Заказ принят в работу.\n"
            "⏳ Примерное время выполнения: {eta} минут\n\n"
            "Статус можно посмотреть прямо в FunPay."
        ),
        requires_db=True,
    ),
    "sent_to_supplier": MessageTemplate(
        key="sent_to_supplier",
        text=(
            "🟢 Заказ передан поставщику.\n\n"
            "Ожидаем выполнение.\n"
            "Как только поставщик завершит работу — мы сразу сообщим."
        ),
        requires_db=False,
    ),
    "processing": MessageTemplate(
        key="processing",
        text=(
            "⏳ Заказ выполняется.\n\n"
            "Пожалуйста, ожидайте.\n"
            "Мы сообщим, как только всё будет готово ❤️"
        ),
        requires_db=False,
    ),
    "completed": MessageTemplate(
        key="completed",
        text=(
            "🎉 Заказ выполнен.\n\n"
            "Услуга уже отправлена.\n"
            "Иногда изменения появляются не мгновенно.\n"
            "Обычно это занимает 5–30 минут.\n"
            "Если спустя это время результата нет — напишите нам.\n\n"
            "Спасибо ❤️"
        ),
        requires_db=True,
    ),
    "completed_reminder": MessageTemplate(
        key="completed_reminder",
        text=(
            "Здравствуйте!\n\n"
            "Если всё уже получили — пожалуйста, подтвердите заказ на FunPay.\n"
            "Это очень помогает магазину ❤️\n\n"
            "Спасибо!"
        ),
        requires_db=True,
    ),
    "thanks": MessageTemplate(
        key="thanks",
        text=(
            "Спасибо!\n\n"
            "Будем рады видеть вас снова ❤️\n"
            "Если понадобится ещё что-нибудь — обязательно возвращайтесь."
        ),
        requires_db=False,
    ),
    "review_prompt": MessageTemplate(
        key="review_prompt",
        text=(
            "Если вам понравилось — будем благодарны за отзыв на FunPay 🙏"
        ),
        requires_db=False,
    ),
    "cancelled": MessageTemplate(
        key="cancelled",
        text="❌ Заказ отменён покупателем.",
        requires_db=True,
    ),
    "refund": MessageTemplate(
        key="refund",
        text=(
            "💸 Заказ #{order_id} отменён.\n\n"
            "Средства возвращены.\n"
            "Если возникнут вопросы — напишите нам."
        ),
        requires_db=True,
    ),
}

DELIVERY_TEMPLATES: Dict[str, MessageTemplate] = {
    "digital_account": MessageTemplate(
        key="digital_account",
        text=(
            "🎁 Ваш товар готов.\n"
            "━━━━━━━━━━━━━━\n"
            "👤 Логин: {login}\n"
            "🔑 Пароль: {password}\n"
            "📧 Почта: {email}\n"
            "━━━━━━━━━━━━━━\n\n"
            "Рекомендуем сразу сменить пароль.\n\n"
            "Спасибо за покупку ❤️"
        ),
        requires_db=True,
    ),
    "link_delivery": MessageTemplate(
        key="link_delivery",
        text=(
            "🎁 Ваша ссылка готова.\n"
            "━━━━━━━━━━━━━━\n"
            "🔗 {link}\n"
            "━━━━━━━━━━━━━━\n\n"
            "Спасибо за покупку ❤️"
        ),
        requires_db=True,
    ),
}

ERROR_TEMPLATES: Dict[str, MessageTemplate] = {
    "supplier_balance_zero": MessageTemplate(
        key="supplier_balance_zero",
        text=(
            "⚠ Сейчас возникла техническая задержка.\n\n"
            "Мы уже пополняем баланс поставщика.\n"
            "Заказ не потерян — он автоматически продолжится после пополнения."
        ),
        requires_db=False,
    ),
    "supplier_error": MessageTemplate(
        key="supplier_error",
        text=(
            "⚠ Возникла проблема у поставщика.\n\n"
            "Мы уже отправили заказ повторно.\n"
            "Обычно это занимает несколько минут.\n"
            "Если потребуется — мы свяжемся с вами."
        ),
        requires_db=False,
    ),
    "site_unavailable": MessageTemplate(
        key="site_unavailable",
        text=(
            "⚠ Сейчас сервис временно недоступен.\n\n"
            "Мы уже получили уведомление.\n"
            "Как только соединение восстановится — заказ автоматически продолжится."
        ),
        requires_db=False,
    ),
    "api_unavailable": MessageTemplate(
        key="api_unavailable",
        text=(
            "⚠ Возникла проблема соединения.\n\n"
            "Мы уже пытаемся восстановить подключение.\n"
            "Ваш заказ сохранен.\n"
            "Повторных действий не требуется."
        ),
        requires_db=False,
    ),
    "limit_exceeded": MessageTemplate(
        key="limit_exceeded",
        text=(
            "Из-за высокой нагрузки выполнение может занять немного больше времени.\n\n"
            "Спасибо за понимание ❤️"
        ),
        requires_db=False,
    ),
    "out_of_stock": MessageTemplate(
        key="out_of_stock",
        text=(
            "К сожалению, товар закончился.\n\n"
            "Мы уже обновляем остатки.\n"
            "Если хотите — можем вернуть средства или предложить альтернативу."
        ),
        requires_db=False,
    ),
}

REVIEW_TEMPLATES: Dict[str, MessageTemplate] = {
    "positive": MessageTemplate(
        key="review_positive",
        text="Спасибо за покупку ❤️ Были рады помочь. Заказ: #{order_id} {order_title}. Если понадобится еще — будем ждать снова 😊",
        requires_db=True,
    ),
    "negative": MessageTemplate(
        key="review_negative",
        text=(
            "Спасибо за отзыв.\n\n"
            "Нам очень жаль, что возникла проблема.\n"
            "Мы уже проверяем ситуацию.\n"
            "Пожалуйста, напишите нам в чат — мы обязательно решим вопрос."
        ),
        requires_db=False,
    ),
    "neutral": MessageTemplate(
        key="review_neutral",
        text=(
            "Спасибо за отзыв!\n"
            "Нам важно ваше мнение.\n"
            "Если были какие-то проблемы — напишите, всё исправим 🤝"
        ),
        requires_db=False,
    ),
}

RECOVERY_TEMPLATES: Dict[str, MessageTemplate] = {
    "supplier_error": MessageTemplate(
        key="recovery_supplier_error",
        text=(
            "⚠ Возникла проблема у поставщика.\n\n"
            "Мы уже отправили заказ повторно.\n"
            "Обычно это занимает несколько минут.\n"
            "Если потребуется — мы свяжемся с вами."
        ),
        requires_db=False,
    ),
    "balance_zero": MessageTemplate(
        key="recovery_balance_zero",
        text=(
            "⚠ Сейчас возникла техническая задержка.\n\n"
            "Мы уже пополняем баланс поставщика.\n"
            "Заказ не потерян — он автоматически продолжится после пополнения."
        ),
        requires_db=False,
    ),
    "site_unavailable": MessageTemplate(
        key="recovery_site_unavailable",
        text=(
            "⚠ Сейчас сервис временно недоступен.\n\n"
            "Мы уже получили уведомление.\n"
            "Как только соединение восстановится — заказ автоматически продолжится."
        ),
        requires_db=False,
    ),
    "api_unavailable": MessageTemplate(
        key="recovery_api_unavailable",
        text=(
            "⚠ Возникла проблема соединения.\n\n"
            "Мы уже пытаемся восстановить подключение.\n"
            "Ваш заказ сохранен.\n"
            "Повторных действий не требуется."
        ),
        requires_db=False,
    ),
    "out_of_stock": MessageTemplate(
        key="recovery_out_of_stock",
        text=(
            "К сожалению, товар закончился.\n\n"
            "Мы уже обновляем остатки.\n"
            "Если хотите — можем вернуть средства или предложить альтернативу."
        ),
        requires_db=False,
    ),
}

NOTIFICATION_TEMPLATES: Dict[str, MessageTemplate] = {
    "admin_new_order": MessageTemplate(
        key="admin_new_order",
        text=("📦 Новый заказ #{order_id}\n" "💰 Сумма: {price}\n" "👤 Покупатель: {buyer}\n" "📋 {order_title}"),
        requires_db=True,
    ),
    "admin_supplier_down": MessageTemplate(
        key="admin_supplier_down",
        text=("🚨 НЕХВАТАЕТ СРЕДСТВ НА {supplier} 🚨\n" "Заказ #{order_id}\n" "Сумма: {price} ₽\n\n" "📌 ПОПОЛНИТЕ {supplier} НА {need} ₽\n" "Лоты сняты с продажи до пополнения."),
        requires_db=False,
    ),
    "admin_refund": MessageTemplate(
        key="admin_refund",
        text=("💸 Возврат по заказу #{order_id}\n" "Покупатель: {buyer}\n" "Сумма: {price}₽"),
        requires_db=True,
    ),
    "admin_plugin_error": MessageTemplate(
        key="admin_plugin_error",
        text=("❌ Ошибка плагина {plugin_name}\n" "Ошибка: {error}\n\n" "Требуется внимание оператора."),
        requires_db=False,
    ),
    "admin_funpay_unavailable": MessageTemplate(
        key="admin_funpay_unavailable",
        text=("⚠ FunPay недоступен\n\n" "Соединение потеряно. Ожидаем восстановления..."),
        requires_db=False,
    ),
    "admin_order_timeout": MessageTemplate(
        key="admin_order_timeout",
        text=("⏱ Заказ #{order_id} висит без движения.\n" "Этап: {stage}\n" "Заказчик: {chat_id}\n" "Сумма: {price}₽"),
        requires_db=False,
    ),
}


PLUGIN_TEMPLATES: Dict[str, MessageTemplate] = {
    "autosmm_message": MessageTemplate(
        key="autosmm_message",
        text="{text}",
        requires_db=False,
    ),
    "donate_message": MessageTemplate(
        key="donate_message",
        text="{text}",
        requires_db=False,
    ),
    "stars_message": MessageTemplate(
        key="stars_message",
        text="{text}",
        requires_db=False,
    ),
    "autoreply_message": MessageTemplate(
        key="autoreply_message",
        text="{text}",
        requires_db=False,
    ),
    "autodelivery_message": MessageTemplate(
        key="autodelivery_message",
        text="{text}",
        requires_db=False,
    ),
}

AUTOREPLY_TEMPLATES: Dict[str, MessageTemplate] = {
    "response": MessageTemplate(
        key="response",
        text="{text}",
        requires_db=False,
    ),
}


AUTODELIVERY_TEMPLATES: Dict[str, MessageTemplate] = {
    "delivery_message": MessageTemplate(
        key="delivery_message",
        text="{text}",
        requires_db=False,
    ),
}


def get_template(category: str, key: str) -> Optional[MessageTemplate]:
    category_map = {
        "order": ORDER_TEMPLATES,
        "delivery": DELIVERY_TEMPLATES,
        "error": ERROR_TEMPLATES,
        "review": REVIEW_TEMPLATES,
        "recovery": RECOVERY_TEMPLATES,
        "notification": NOTIFICATION_TEMPLATES,
        "plugin": PLUGIN_TEMPLATES,
        "autoreply": AUTOREPLY_TEMPLATES,
        "autodelivery": AUTODELIVERY_TEMPLATES,
    }
    container = category_map.get(category)
    if not container:
        return None
    return container.get(key)
