import os
import json
import time
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
BOT_TOKEN = "8892037838:AAFjs24BVp5_JW5Qc5GqTjNCjSMmNcyxLBA"
CHAT_ID = -1004422275359  # замени на ID твоего канала

INBOX = PROJECT_ROOT / "inbox"

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def download_file(file_id, dest_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return False
    file_path = resp.json()["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    r = requests.get(file_url, stream=True)
    if r.status_code == 200:
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    return False

def apply_task(package):
    INBOX.mkdir(exist_ok=True)
    task_file = INBOX / f"task_{package.get('task_id', 'unknown')}_{int(time.time())}.json"
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2)
    send_message(f"✅ Задача {package.get('task_id')} получена, обновляю проект...")

def main():
    last_update = 0
    print("Telegram агент (с поддержкой файлов) запущен, ожидаю задачи...")
    while True:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"offset": last_update + 1, "timeout": 30}
        try:
            resp = requests.get(url, params=params, timeout=35)
            data = resp.json()
            for update in data.get("result", []):
                last_update = update["update_id"]
                msg = update.get("channel_post") or update.get("message")
                if not msg:
                    continue
                # Обработка текстового JSON
                if msg.get("text"):
                    try:
                        package = json.loads(msg["text"])
                        if package.get("approved") and package.get("files"):
                            apply_task(package)
                    except:
                        pass
                # Обработка документа (файла)
                if msg.get("document"):
                    file_id = msg["document"]["file_id"]
                    file_name = msg["document"].get("file_name", "task.json")
                    temp_file = PROJECT_ROOT / f"temp_{int(time.time())}.json"
                    if download_file(file_id, temp_file):
                        try:
                            with open(temp_file, "r", encoding="utf-8") as f:
                                package = json.load(f)
                            if package.get("approved") and package.get("files"):
                                apply_task(package)
                        except Exception as e:
                            print(f"Ошибка обработки файла: {e}")
                        temp_file.unlink()
        except Exception as e:
            print(f"Ошибка: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()