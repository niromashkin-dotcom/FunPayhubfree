import json
import os
import platform
import uuid

def get_cursor_config_path():
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        return os.path.join(home, "AppData", "Roaming", "Cursor", "User", "globalStorage", "storage.json")
    elif platform.system() == "Darwin":  # macOS
        return os.path.join(home, "Library", "Application Support", "Cursor", "User", "globalStorage", "storage.json")
    else:  # Linux
        return os.path.join(home, ".config", "Cursor", "User", "globalStorage", "storage.json")

def reset_cursor_ids():
    config_path = get_cursor_config_path()
    
    if not os.path.exists(config_path):
        print(f"[ERROR] Config file not found: {config_path}")
        print("Make sure Cursor is installed and you have launched it at least once.")
        return

    # Читаем текущие настройки
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"[ERROR] JSON read error: {e}")
            return

    # Генерируем абсолютно новые случайные ID железа
    new_telemetry_id = str(uuid.uuid4())
    new_mac_machine_id = str(uuid.uuid4())
    new_machine_id = str(uuid.uuid4())
    new_dev_device_id = str(uuid.uuid4())

    # Перезаписываем ключи
    data["telemetry.machineId"] = new_telemetry_id
    data["platform.macMachineId"] = new_mac_machine_id
    data["telemetry.macMachineId"] = new_mac_machine_id
    data["telemetry.devDeviceId"] = new_dev_device_id
    data["machineId"] = new_machine_id 

    # Сохраняем обновленный файл
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print("[SUCCESS] Hardware IDs for Cursor successfully reset!")
    print("--------------------------------------------------")
    print("What to do next:")
    print("1. Log Out from your current account in Cursor (or do it before closing).")
    print("2. Go to any temporary mail service (e.g., temp-mail.org).")
    print("3. Register a NEW account in Cursor and confirm the code from the email.")
    print("Done! You have a fresh Pro-account with new Fast-requests.")

if __name__ == "__main__":
    print("=== Cursor ID Modifier for Infinite Trial ===")
    confirm = input("Did you close Cursor before running the script? (y/n): ")
    if confirm.lower() == 'y':
        reset_cursor_ids()
    else:
        print("[ERROR] Close Cursor first, so it won't overwrite the configuration back!")