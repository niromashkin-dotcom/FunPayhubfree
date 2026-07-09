import os
import configparser
from security.secrets_manager import SecretsManager

def migrate_config_file(file_path: str, secrets_manager: SecretsManager):
    config = configparser.ConfigParser(delimiters=(":",), interpolation=None)
    config.optionxform = str
    config.read(file_path, encoding="utf-8")

    # FunPay Golden Key
    if "FunPay" in config and "golden_key" in config["FunPay"]:
        old_key = config["FunPay"]["golden_key"]
        if old_key and not old_key.startswith("gAAAAAB"):
            encrypted_key = secrets_manager.encrypt_secret(old_key)
            config["FunPay"]["golden_key"] = encrypted_key
            print(f"[MIGRATE] Encrypted FunPay.golden_key in {file_path}")

    # Telegram Bot Token
    if "Telegram" in config and "token" in config["Telegram"]:
        old_token = config["Telegram"]["token"]
        if old_token and not old_token.startswith("gAAAAAB"):
            encrypted_token = secrets_manager.encrypt_secret(old_token)
            config["Telegram"]["token"] = encrypted_token
            print(f"[MIGRATE] Encrypted Telegram.token in {file_path}")

    with open(file_path, "w", encoding="utf-8") as f:
        config.write(f)

def main():
    secrets_manager = SecretsManager()
    encryption_key = secrets_manager.get_encryption_key()

    if not os.getenv('ENCRYPTION_KEY'):
        print("\n🔥 GRILL ME REPORT:")
        print("  КРИТИЧЕСКАЯ УЯЗВИМОСТЬ: Переменная окружения ENCRYPTION_KEY не установлена.")
        print("  Будет сгенерирован новый ключ, но он НЕ будет сохранен автоматически.")
        print("  СРОЧНО: Установите ENCRYPTION_KEY в переменных окружения или .env файл.")
        print(f"  Пример ENCRYPTION_KEY (сохраните его!): {encryption_key.decode()}\n")

    print("Начинается миграция конфигов...")

    # Migrate _main.cfg
    main_config_path = os.path.join("configs", "_main.cfg")
    if os.path.exists(main_config_path):
        migrate_config_file(main_config_path, secrets_manager)
    else:
        print(f"[SKIP] {main_config_path} не найден.")

    # Migrate telegram_notifier_plugin.json (if it exists and has bot_token)
    tg_plugin_config_path = os.path.join("configs", "plugins", "telegram_notifier_plugin.json")
    if os.path.exists(tg_plugin_config_path):
        try:
            with open(tg_plugin_config_path, "r", encoding="utf-8") as f:
                tg_cfg = json.load(f)
            old_token = tg_cfg.get("bot_token", "")
            if old_token and not old_token.startswith("gAAAAAB"):
                encrypted_token = secrets_manager.encrypt_secret(old_token)
                tg_cfg["bot_token"] = encrypted_token
                with open(tg_plugin_config_path, "w", encoding="utf-8") as f:
                    json.dump(tg_cfg, f, indent=2, ensure_ascii=False)
                print(f"[MIGRATE] Encrypted bot_token in {tg_plugin_config_path}")
            else:
                print(f"[SKIP] bot_token в {tg_plugin_config_path} уже зашифрован или отсутствует.")
        except Exception as e:
            print(f"[ERROR] Ошибка при обработке {tg_plugin_config_path}: {e}")
    else:
        print(f"[SKIP] {tg_plugin_config_path} не найден.")

    print("Миграция конфигов завершена.")

if __name__ == "__main__":
    # Ensure json is imported for telegram_notifier_plugin.json migration
    import json
    main()
