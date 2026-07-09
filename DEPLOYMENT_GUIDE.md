# 🚀 РАЗВЕРТЫВАНИЕ FUNPAYHUB НА RAILWAY.APP

## 📋 ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

1. **Аккаунт на Railway.app**: [Зарегистрируйтесь](https://docs.railway.app/tutorials/telegram-bot)
2. **Telegram Bot Token**: [Создайте бота](https://core.telegram.org/bots/tutorial)
3. **FunPay Golden Key**: [Получите в FunPay](https://funpay.com/en/help/api/)
4. **GitHub аккаунт** (опционально, для авторазвертывания)

## 🛠️ УСТАНОВКА RAILWAY CLI

### Windows:
```powershell
npm install -g @railway/cli
railway login
```

### Linux/Mac:
```bash
curl -fsSL https://railway.app/install.sh | sh
railway login
```

## 🔧 КОНФИГУРАЦИЯ ПРОЕКТА

### 1. Создайте .env файл:
```bash
cp .env.example .env
# Отредактируйте .env, заполните все переменные
```

### 2. Ключевые переменные окружения:

⚠️ Актуальный и полный список переменных — всегда смотрите `.env.example` в корне проекта,
он синхронизирован с кодом. Ниже — то, что специфично именно для деплоя на Railway
(headless-режим добавлен в сессии от 08.07.2026):

```env
# Обязательные для FunPay-ядра:
GOLDEN_KEY=ваш_golden_key_из_cookies_funpay.com
TELEGRAM_BOT_TOKEN=токен_вашего_бота   # для tg_bot_service.py (Control Panel)

# Обязательно для Railway (headless) — иначе приложение попытается открыть desktop-окно:
FUNPAYHUB_HEADLESS=1
# Railway сам подставляет $PORT — funpayhub_main.py подхватывает его автоматически.

# Обязательно, раз приложение слушает 0.0.0.0 в headless-режиме — иначе /api/* заблокирован по умолчанию:
FUNPAYHUB_API_TOKEN=длинная_случайная_строка

# Опциональные:
LOG_LEVEL=INFO
FUNPAY_CHECK_INTERVAL=300
```

Примечание: переменной `ENCRYPTED_GOLDEN_KEY` в текущем коде не существует — это осталось
от более старой черновой версии этого гайда. Правильное имя — `GOLDEN_KEY` (см. `.env.example`).

## 🚀 РАЗВЕРТЫВАНИЕ

### Способ 1: Через Railway CLI (рекомендуется)
```bash
# Инициализация проекта
railway init

# Загрузка переменных окружения
railway variables set ENCRYPTION_KEY="ваш_ключ"
railway variables set ENCRYPTED_GOLDEN_KEY="зашифрованный_ключ"
railway variables set TELEGRAM_BOT_TOKEN="токен_бота"

# Деплой
railway up
```

### Способ 2: Через GitHub (авторазвертывание)
1. Создайте репозиторий на GitHub
2. Подключите Railway к репозиторию
3. Настройте переменные окружения в Railway Dashboard
4. Railway будет автоматически деплоить при пуше в main

### Способ 3: Через Railway Dashboard
1. Перейдите на [Railway.app](https://railway.app)
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите ваш репозиторий
5. Настройте переменные окружения

## 🔍 ТЕСТИРОВАНИЕ РАЗВЕРТЫВАНИЯ

### 1. Проверка доступности:
```bash
# Получите URL вашего проекта
railway status

# Проверьте health check
curl https://ваш-проект.railway.app/health
```

### 2. Проверка Telegram бота:
1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Проверьте ответ

### 3. Проверка FunPay интеграции:
```bash
# Запустите тестовый скрипт
python test_golden_key.py
```

## ⚙️ НАСТРОЙКА 24/7 МОНИТОРИНГА

### 1. UptimeRobot (бесплатно):
1. Зарегистрируйтесь на [UptimeRobot](https://uptimerobot.com/)
2. Добавьте монитор для вашего Railway URL
3. Настройте проверку каждые 5 минут
4. Добавьте уведомления в Telegram

### 2. Railway Logs:
```bash
# Просмотр логов в реальном времени
railway logs

# Экспорт логов
railway logs --export > logs.txt
```

### 3. Grafana Cloud (бесплатный tier):
1. Создайте аккаунт на [Grafana Cloud](https://grafana.com/products/cloud/)
2. Настройте мониторинг метрик
3. Добавьте дашборды для отслеживания

## 🛠️ УСТРАНЕНИЕ НЕИСПРАВНОСТЕЙ

### Проблема: Приложение не запускается
```bash
# Проверьте логи
railway logs

# Проверьте переменные окружения
railway variables list

# Перезапустите сервис
railway restart
```

### Проблема: Telegram бот не отвечает
1. Проверьте TELEGRAM_BOT_TOKEN в переменных окружения
2. Проверьте, что бот активирован в BotFather
3. Проверьте логи бота:
```bash
railway logs --service telegram
```

### Проблема: Нет доступа к FunPay API
1. Проверьте `GOLDEN_KEY` (это cookie сессии, а не отдельно зашифрованное значение —
   если долго не логинились на funpay.com, он мог протухнуть, тогда нужно перелогиниться
   и взять новый из cookies браузера)
2. Проверьте интернет-соединение на сервере
3. Проверьте лимиты API FunPay

### Проблема: 401 Unauthorized на /api/*
Это ожидаемое поведение в headless-режиме без заданного `FUNPAYHUB_API_TOKEN` (защита от
случайно открытого наружу API — см. `.env.example`). Задайте `FUNPAYHUB_API_TOKEN` и
передавайте его в заголовке `X-API-Token` при обращении к `/api/*`.

## 📊 МОНИТОРИНГ И АНАЛИТИКА

### Ключевые метрики для отслеживания:
1. **Uptime**: Должен быть >99.9%
2. **Response Time**: <500ms
3. **Error Rate**: <1%
4. **Заказов в день**: Целевой показатель
5. **Выручка**: Ежедневный мониторинг

### Настройка алертов:
```yaml
# Пример конфигурации алертов
alerts:
  - name: "High Error Rate"
    condition: "error_rate > 5%"
    channels: ["telegram", "email"]
    
  - name: "Service Down"
    condition: "uptime < 95%"
    channels: ["telegram", "sms"]
```

## 💾 БЭКАПЫ И ВОССТАНОВЛЕНИЕ

### Автоматические бэкапы:
```bash
# Скрипт для бэкапа
#!/bin/bash
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf $BACKUP_FILE --exclude="__pycache__" --exclude="*.pyc" .
railway variables set BACKUP_URL="$(railway upload $BACKUP_FILE)"
```

### Восстановление из бэкапа:
```bash
# Скачайте бэкап
railway variables get BACKUP_URL

# Распакуйте и восстановите
tar -xzf backup.tar.gz
railway up
```

## 📈 ОПТИМИЗАЦИЯ И МАСШТАБИРОВАНИЕ

### Когда масштабировать:
1. >100 заказов в день
2. >50 одновременных пользователей
3. Response time >1000ms

### Шаги масштабирования:
1. Увеличьте ресурсы в Railway
2. Добавьте кэширование (Redis)
3. Оптимизируйте базу данных
4. Добавьте балансировщик нагрузки

## 🔗 ПОЛЕЗНЫЕ ССЫЛКИ

- [Railway Documentation](https://docs.railway.app/tutorials/telegram-bot)
- [Telegram Bot API](https://core.telegram.org/bots/tutorial)
- [FunPay API Docs](https://funpay.com/en/help/api/)
- [UptimeRobot](https://uptimerobot.com/)
- [Grafana Cloud](https://grafana.com/products/cloud/)

## 🆘 ПОДДЕРЖКА

### Каналы поддержки:
1. **Railway Discord**: [ссылка](https://discord.gg/railway)
2. **Telegram Community**: @funpayhub_support
3. **GitHub Issues**: [репозиторий](https://github.com/ваш-username/funpayhub/issues)

### Частые вопросы:
**Q: Сколько стоит Railway?**  
A: Бесплатный tier включает 5$ кредитов в месяц, достаточно для 24/7 работы.

**Q: Как продлить бесплатный период?**  
A: Railway автоматически продлевает кредиты каждый месяц.

**Q: Что делать если закончились кредиты?**  
A: Можно перейти на Render.com или PythonAnywhere.

---
*Документация создана: 08.07.2026 00:14:21*
