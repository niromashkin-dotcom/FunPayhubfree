#!/bin/bash
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
