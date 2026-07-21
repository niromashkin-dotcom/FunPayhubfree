import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv("/opt/funpayhub/source/.env" if os.path.exists("/opt/funpayhub/source/.env") else ".env")

BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "").strip().strip('"').strip("'")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip().strip('"').strip("'")
CORE_SERVICE_NAME = os.getenv("CORE_SERVICE_NAME", "funpayhub-core").strip()
