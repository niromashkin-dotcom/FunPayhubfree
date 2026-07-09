#!/usr/bin/env python3
"""
Скрипт для генерации SHA256 хэша пароля для конфигурации Telegram бота.
"""

import hashlib
import sys

def main():
    print("=== Генерация хэша пароля для Telegram бота ===")
    
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Введите пароль для авторизации в Telegram боте: ")
    
    if not password:
        print("❌ Пароль не может быть пустым")
        return
    
    # Генерация SHA256 хэша
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    print(f"\n✅ Хэш пароля успешно сгенерирован:")
    print(f"Пароль: {password}")
    print(f"SHA256 хэш: {password_hash}")
    
    print(f"\n📝 Пример конфигурации для файла tg_bot/authorized_users.json:")
    print(f"""{{
  "version": "1.0",
  "description": "Whitelist авторизованных пользователей Telegram бота",
  "authorized_users": [123456789],  // Ваш user_id Telegram
  "enable_password_auth": true,
  "password_hash": "{password_hash}"
}}""")
    
    print(f"\n💡 Использование:")
    print(f"1. Замените '123456789' на ваш Telegram user_id")
    print(f"2. Добавьте хэш в файл tg_bot/authorized_users.json")
    print(f"3. Для авторизации в боте используйте команду: /auth {password}")

if __name__ == "__main__":
    main()