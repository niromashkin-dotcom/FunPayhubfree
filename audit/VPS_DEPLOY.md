# Подготовка к запуску на VPS

Рекомендации по развертыванию (Deployment Guide).

## 1. Требования к серверу
- Linux (Ubuntu 22.04+ или Debian 12+)
- Python 3.11+
- SQLite3 (обязательно поддержка WAL)
- PM2 (через Node.js) или Systemd для управления демоном.

## 2. Первичная настройка
```bash
# Клонирование репозитория
git clone <repo_url> /opt/funpayhub
cd /opt/funpayhub

# Установка зависимостей
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка секретов
cp .env.example .env
nano .env # Вписать токен FunPay (golden_key) и ключи поставщиков
```

## 3. Запуск через PM2 (рекомендуется)
```bash
pm2 start run_bot.py --name "FunPayHub" --interpreter venv/bin/python
pm2 save
pm2 startup
```

## 4. Backups (Обязательно!)
Рекомендуется настроить Cron на сервере для создания ежедневных бэкапов:
```cron
0 3 * * * sqlite3 /opt/funpayhub/database.db ".backup '/opt/funpayhub/backups/db_backup_$(date +\%F).db'"
```
