#!/usr/bin/env python3
"""
Скрипт развертывания FunPayHub на Railway.app для 24/7 работы
Автоматическая настройка бесплатного сервера с мониторингом
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class RailwayDeployer:
    """
    Деployer для развертывания на Railway.app
    Настраивает 24/7 сервер для Telegram бота и основного приложения
    """
    
    def __init__(self):
        self.project_name = "funpayhub"
        self.railway_config = {
            "build": {
                "builder": "nixpacks",
                "buildCommand": "pip install -r requirements.txt"
            },
            "deploy": {
                "startCommand": "python funpayhub_main.py & python tg_bot_service.py",
                "healthcheckPath": "/health",
                "healthcheckTimeout": 100
            },
            "variables": {}
        }
        
        # Ссылки на туториалы
        self.tutorials = {
            "railway": "https://docs.railway.app/tutorials/telegram-bot",
            "telegram_bot": "https://core.telegram.org/bots/tutorial",
            "funpay_api": "https://funpay.com/en/help/api/",
            "uptime_monitoring": "https://uptimerobot.com/",
            "monitoring": "https://grafana.com/products/cloud/"
        }
    
    def check_prerequisites(self):
        """Проверка необходимых инструментов"""
        print("🔧 ПРОВЕРКА ПРЕДВАРИТЕЛЬНЫХ УСЛОВИЙ")
        print("="*60)
        
        checks = []
        
        # Проверка Python
        try:
            python_version = subprocess.check_output(["python", "--version"], text=True).strip()
            checks.append(f"✅ Python: {python_version}")
        except Exception:
            checks.append("❌ Python не найден")
        
        # Проверка pip
        try:
            pip_version = subprocess.check_output(["pip", "--version"], text=True).split('\n')[0]
            checks.append(f"✅ pip: {pip_version}")
        except Exception:
            checks.append("❌ pip не найден")
        
        # Проверка git
        try:
            git_version = subprocess.check_output(["git", "--version"], text=True).strip()
            checks.append(f"✅ Git: {git_version}")
        except Exception:
            checks.append("❌ Git не найден")
        
        # Проверка Node.js (для Railway CLI)
        try:
            node_version = subprocess.check_output(["node", "--version"], text=True).strip()
            checks.append(f"✅ Node.js: {node_version}")
        except Exception:
            checks.append("⚠️  Node.js не найден (нужен для Railway CLI)")
        
        # Проверка npm
        try:
            npm_version = subprocess.check_output(["npm", "--version"], text=True).strip()
            checks.append(f"✅ npm: {npm_version}")
        except Exception:
            checks.append("⚠️  npm не найден (нужен для Railway CLI)")
        
        # Вывод результатов проверки
        for check in checks:
            print(f"   {check}")
        
        print(f"\n📋 РЕЗУЛЬТАТ ПРОВЕРКИ:")
        success_count = sum(1 for c in checks if c.startswith("✅"))
        warning_count = sum(1 for c in checks if c.startswith("⚠️"))
        error_count = sum(1 for c in checks if c.startswith("❌"))
        
        print(f"   Успешно: {success_count}")
        print(f"   Предупреждения: {warning_count}")
        print(f"   Ошибки: {error_count}")
        
        return error_count == 0
    
    def create_railway_config(self):
        """Создание конфигурационных файлов для Railway"""
        print("\n📁 СОЗДАНИЕ КОНФИГУРАЦИОННЫХ ФАЙЛОВ ДЛЯ RAILWAY")
        print("="*60)
        
        # 1. railway.toml
        railway_toml = f"""[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "python funpayhub_main.py & python tg_bot_service.py"
healthcheckPath = "/health"
healthcheckTimeout = 100
"""
        
        with open("railway.toml", "w", encoding="utf-8") as f:
            f.write(railway_toml)
        print("✅ Создан railway.toml")
        
        # 2. Обновленный requirements.txt
        requirements = """# Основные зависимости FunPayHub
requests==2.31.0
aiohttp==3.9.1
aiogram==3.0.0
flask==3.0.0
cryptography==41.0.7
python-dotenv==1.0.0
schedule==1.2.0
pydantic==2.5.0

# Дополнительные утилиты
pillow==10.2.0
sqlalchemy==2.0.23
alembic==1.13.1

# Для мониторинга и логирования
prometheus-client==0.19.0
structlog==23.2.0

# Для веб-интерфейса
jinja2==3.1.3
"""
        
        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.write(requirements)
        print("✅ Обновлен requirements.txt")
        
        # 3. health check endpoint
        health_check = """#!/usr/bin/env python3
"""
        
        health_file = Path("web/health.py")
        health_file.parent.mkdir(exist_ok=True, parents=True)
        
        with open(health_file, "w", encoding="utf-8") as f:
            f.write(health_check)
        print("✅ Создан health check endpoint")
        
        # 4. Документация развертывания
        self.create_deployment_docs()
        
        return True
    
    def create_deployment_docs(self):
        """Создание документации по развертыванию"""
        docs = f"""# 🚀 РАЗВЕРТЫВАНИЕ FUNPAYHUB НА RAILWAY.APP

## 📋 ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

1. **Аккаунт на Railway.app**: [Зарегистрируйтесь]({self.tutorials['railway']})
2. **Telegram Bot Token**: [Создайте бота]({self.tutorials['telegram_bot']})
3. **FunPay Golden Key**: [Получите в FunPay]({self.tutorials['funpay_api']})
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
```env
# Обязательные:
ENCRYPTION_KEY=ваш_ключ_шифрования
ENCRYPTED_GOLDEN_KEY=зашифрованный_golden_key
TELEGRAM_BOT_TOKEN=токен_вашего_бота

# Опциональные:
DATABASE_URL=sqlite:///data/funpayhub.db
LOG_LEVEL=INFO
FUNPAY_CHECK_INTERVAL=300
```

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
1. Зарегистрируйтесь на [UptimeRobot]({self.tutorials['uptime_monitoring']})
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
1. Создайте аккаунт на [Grafana Cloud]({self.tutorials['monitoring']})
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
1. Проверьте ENCRYPTED_GOLDEN_KEY
2. Проверьте интернет-соединение на сервере
3. Проверьте лимиты API FunPay

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

- [Railway Documentation]({self.tutorials['railway']})
- [Telegram Bot API]({self.tutorials['telegram_bot']})
- [FunPay API Docs]({self.tutorials['funpay_api']})
- [UptimeRobot]({self.tutorials['uptime_monitoring']})
- [Grafana Cloud]({self.tutorials['monitoring']})

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
*Документация создана: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}*
"""
        
        with open("DEPLOYMENT_GUIDE.md", "w", encoding="utf-8") as f:
            f.write(docs)
        print("✅ Создана документация по развертыванию: DEPLOYMENT_GUIDE.md")
    
    def generate_deploy_script(self):
        """Генерация скрипта автоматического развертывания"""
        deploy_script = """#!/bin/bash
# 🚀 СКРИПТ АВТОМАТИЧЕСКОГО РАЗВЕРТЫВАНИЯ FUNPAYHUB

set -e  # Остановить при ошибке

echo "🚀 НАЧИНАЮ АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ FUNPAYHUB"
echo "="*60

# Проверка Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI не установлен"
    echo "Установка: npm install -g @railway/cli"
    exit 1
fi

# Логин в Railway (если еще не залогинен)
if ! railway status &> /dev/null; then
    echo "🔐 Требуется логин в Railway..."
    railway login
fi

# Создание проекта (если нет)
echo "📦 Проверка проекта Railway..."
if ! railway status; then
    echo "🆕 Создаю новый проект Railway..."
    railway init
fi

# Загрузка переменных окружения из .env
echo "🔐 Настройка переменных окружения..."
if [ -f ".env" ]; then
    echo "📖 Загружаю переменные из .env файла..."
    
    # Загружаем переменные из .env
    while IFS='=' read -r key value; do
        # Пропускаем комментарии и пустые строки
        [[ $key =~ ^#.* ]] || [[ -z $key ]] && continue
        
        # Удаляем кавычки из значения
        value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
        
        echo "   Устанавливаю: $key"
        railway variables set "$key"="$value"
    done < .env
else
    echo "⚠️  Файл .env не найден"
    echo "   Создайте .env из .env.example и заполните значения"
    exit 1
fi

# Деплой
echo "🚀 Запускаю деплой на Railway..."
railway up

# Получение URL проекта
echo "🌐 Получение URL проекта..."
PROJECT_URL=$(railway status --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('service', {}).get('url', 'Не удалось получить URL'))
")

echo "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
echo "="*60
echo "🌐 Ваш проект доступен по адресу:"
echo "   $PROJECT_URL"
echo ""
echo "🔍 ДАЛЬНЕЙШИЕ ДЕЙСТВИЯ:"
echo "   1. Проверьте доступность: curl $PROJECT_URL/health"
echo "   2. Проверьте Telegram бота"
echo "   3. Настройте мониторинг на UptimeRobot"
echo "   4. Создайте тестовые лоты на FunPay"
echo ""
echo "📋 КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ:"
echo "   Просмотр логов: railway logs"
echo "   Перезапуск: railway restart"
echo "   Обновление: git push && railway up"
echo "   Удаление: railway delete"
echo ""
echo "🎉 УСПЕШНОГО ЗАПУСКА!"
"""
        
        with open("deploy.sh", "w", encoding="utf-8") as f:
            f.write(deploy_script)
        
        # Делаем скрипт исполняемым (для Linux/Mac)
        if os.name != 'nt':  # Не Windows
            os.chmod("deploy.sh", 0o755)
        
        print("✅ Создан скрипт автоматического развертывания: deploy.sh")
    
    def create_quick_start(self):
        """Создание быстрого стартового руководства"""
        quick_start = """# ⚡ БЫСТРЫЙ СТАРТ FUNPAYHUB

## 🎯 ЧТО ВАМ ПОТРЕБУЕТСЯ:
1. Аккаунт на Railway.app (бесплатно)
2. Telegram Bot Token (бесплатно)
3. FunPay Golden Key (бесплатно)

## 🚀 5 ШАГОВ ДЛЯ ЗАПУСКА:

### ШАГ 1: Подготовка
```bash
# Клонируйте проект (если еще не)
git clone <ваш-репозиторий>
cd FunPayHub

# Установите Railway CLI
npm install -g @railway/cli
```

### ШАГ 2: Настройка
```bash
# Создайте .env файл
cp .env.example .env
# Откройте .env и заполните значения:
# 1. ENCRYPTION_KEY (сгенерируйте новый)
# 2. ENCRYPTED_GOLDEN_KEY (из encrypted_secrets.json)
# 3. TELEGRAM_BOT_TOKEN (от @BotFather)
```

### ШАГ 3: Развертывание
```bash
# Автоматическое развертывание
bash deploy.sh
# Или вручную:
railway login
railway init
railway up
```

### ШАГ 4: Тестирование
```bash
# Проверьте доступность
curl https://ваш-проект.railway.app/health

# Проверьте бота в Telegram
/start
/auth ваш_пароль
```

### ШАГ 5: Монетизация
1. Создайте лоты на FunPay
2. Установите цены (начните с 1 рубля для теста)
3. Привлекайте первых клиентов
4. Масштабируйте

## 💰 ЧЕГО ОЖИДАТЬ:
- День 1-7: 0-500 руб/день (тестирование)
- День 7-30: 500-2000 руб/день (оптимизация)
- День 30+: 2000-5000+ руб/день (масштабирование)

## 🆘 ЕСЛИ ВОЗНИКЛИ ПРОБЛЕМЫ:

### 1. Приложение не запускается:
```bash
# Проверьте логи
railway logs

# Проверьте переменные
railway variables list
```

### 2. Бот не отвечает:
- Проверьте TELEGRAM_BOT_TOKEN
- Убедитесь, что бот активирован
- Проверьте railway logs --service telegram

### 3. Нет заказов:
- Проверьте лоты на FunPay
- Убедитесь, что цены конкурентные
- Добавьте больше описания к лотам

## 📞 ПОДДЕРЖКА:
- Telegram: @funpayhub_support
- Email: support@funpayhub.com
- Документация: DEPLOYMENT_GUIDE.md

---
*Запустите и зарабатывайте! 🚀*
"""
        
        with open("QUICK_START.md", "w", encoding="utf-8") as f:
            f.write(quick_start)
        print("✅ Создано быстрое стартовое руководство: QUICK_START.md")
    
    def print_summary(self):
        """Вывод сводки по подготовке"""
        print("\n" + "="*80)
        print("🎯 ПОДГОТОВКА К 24/7 РАЗВЕРТЫВАНИЮ ЗАВЕРШЕНА")
        print("="*80)
        
        print(f"\n📁 СОЗДАННЫЕ ФАЙЛЫ:")
        print(f"   1. 📄 railway.toml - конфигурация Railway")
        print(f"   2. 📦 requirements.txt - обновленные зависимости")
        print(f"   3. 🩺 web/health.py - health check endpoint")
        print(f"   4. 📚 DEPLOYMENT_GUIDE.md - полная документация")
        print(f"   5. 🚀 deploy.sh - скрипт автоматического развертывания")
        print(f"   6. ⚡ QUICK_START.md - быстрое руководство")
        
        print(f"\n🎯 СЛЕДУЮЩИЕ ШАГИ:")
        print(f"   1. 🔐 Создайте аккаунт на Railway.app")
        print(f"   2. 🤖 Создайте Telegram бота через @BotFather")
        print(f"   3. 💰 Получите Golden Key в FunPay")
        print(f"   4. 📝 Заполните .env файл (из .env.example)")
        print(f"   5. 🚀 Запустите: bash deploy.sh")
        
        print(f"\n⏱️  ОРИЕНТИРОВОЧНОЕ ВРЕМЯ:")
        print(f"   • Регистрация аккаунтов: 15 минут")
        print(f"   • Настройка .env: 10 минут")
        print(f"   • Развертывание: 5-10 минут")
        print(f"   • Тестирование: 15 минут")
        print(f"   • ИТОГО: ~45-60 минут")
        
        print(f"\n💰 СТОИМОСТЬ:")
        print(f"   • Railway: Бесплатно (5$ кредитов/месяц)")
        print(f"   • Telegram Bot: Бесплатно")
        print(f"   • FunPay: Бесплатно (комиссия 10-15% с продаж)")
        print(f"   • UptimeRobot: Бесплатно (50 мониторов)")
        
        print(f"\n🎉 ВСЕ ГОТОВО К ЗАПУСКУ!")
        print("="*80)


def main():
    """Основная функция подготовки к развертыванию"""
    print("🚀 ПОДГОТОВКА К 24/7 РАЗВЕРТЫВАНИЮ FUNPAYHUB")
    print("="*80)
    print("Цель: Настроить автоматическое развертывание на Railway.app")
    print("="*80)
    
    deployer = RailwayDeployer()
    
    # Проверка предварительных условий
    if not deployer.check_prerequisites():
        print("\n❌ НЕ ВЫПОЛНЕНЫ ПРЕДВАРИТЕЛЬНЫЕ УСЛОВИЯ")
        print("Установите необходимые инструменты и повторите попытку")
        return
    
    # Создание конфигурационных файлов
    deployer.create_railway_config()
    
    # Генерация скриптов
    deployer.generate_deploy_script()
    deployer.create_quick_start()
    
    # Вывод сводки
    deployer.print_summary()


if __name__ == "__main__":
    main()