# Деплой FunPayHub на 24/7 сервер

## Требования
- Linux сервер (Ubuntu 20.04+)
- Python 3.9+
- systemd
- Пользователь `funpayhub` (для безопасности)

## Шаг 1 — Подготовка сервера

1. Подключись по SSH:
   ssh user@server_ip

2. Создай пользователя funpayhub:
   sudo useradd -m -s /bin/bash funpayhub

3. Установи зависимости:
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv git

4. Клонируй проект:
   cd /home/funpayhub
   sudo git clone https://github.com/YOUR_REPO/FunPayHub.git
   sudo chown -R funpayhub:funpayhub FunPayHub

## Шаг 2 — Установка зависимостей Python

cd /home/funpayhub/FunPayHub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

## Шаг 3 — Настройка переменных окружения

sudo nano /home/funpayhub/.env

Вставь значения (от пользователя funpayhub):
- GOLDEN_KEY=xxxxxxx
- TELEGRAM_BOT_TOKEN=xxxxxxx
- TELEGRAM_ADMIN_CHAT_ID=xxxxxxx
- Остальные API-ключи

Сохрани: CTRL+X, Y, Enter

## Шаг 4 — Установка systemd сервисов

1. Скопируй конфиги:
   sudo cp deploy/funpayhub-bot.service /etc/systemd/system/
   sudo cp deploy/funpayhub-app.service /etc/systemd/system/

2. Перезагрузи systemd:
   sudo systemctl daemon-reload

3. Включи сервисы:
   sudo systemctl enable funpayhub-bot.service
   sudo systemctl enable funpayhub-app.service

## Шаг 5 — Запуск сервисов

sudo systemctl start funpayhub-bot.service
sudo systemctl start funpayhub-app.service

Проверь статус:
sudo systemctl status funpayhub-bot.service
sudo systemctl status funpayhub-app.service

## Логи

Telegram бот: tail -f /var/log/funpayhub/bot.log
Приложение: tail -f /var/log/funpayhub/app.log

## Управление

Перезагрузить бота: sudo systemctl restart funpayhub-bot.service
Перезагрузить приложение: sudo systemctl restart funpayhub-app.service
Остановить: sudo systemctl stop funpayhub-bot.service

## Интеграция Bot ↔ App

В .env (на сервере) добавь:
FUNPAYHUB_API_URL=http://localhost:5000
FUNPAYHUB_API_TOKEN=xxxxxxx (тот же токен что в приложении)

Telegram бот будет дергать приложение через этот URL.