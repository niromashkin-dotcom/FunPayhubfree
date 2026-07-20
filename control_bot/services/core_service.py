import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("ControlBot.CoreService")

class CoreService:
    def __init__(self, service_name: str = "funpayhub-core"):
        self.service_name = service_name

    def _run_systemctl(self, action: str) -> bool:
        """Вспомогательный метод для запуска команд systemctl."""
        try:
            cmd = ["systemctl", action, self.service_name]
            # Запуск с таймаутом, чтобы избежать вечного зависания
            subprocess.run(cmd, check=True, timeout=10)
            logger.info(f"Successfully executed systemctl {action} for {self.service_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to execute systemctl {action} for {self.service_name}: {e}")
            return False

    def start(self) -> bool:
        return self._run_systemctl("start")

    def stop(self) -> bool:
        return self._run_systemctl("stop")

    def restart(self) -> bool:
        return self._run_systemctl("restart")

    def status(self) -> Dict[str, Any]:
        """Получает статус службы через systemctl show."""
        try:
            cmd = ["systemctl", "show", self.service_name, "--property=ActiveState,SubState,MainPID,ActiveEnterTimestamp"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            props = {}
            for line in res.stdout.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
            
            return {
                "name": self.service_name,
                "active": props.get("ActiveState") == "active",
                "status": props.get("ActiveState", "unknown"),
                "sub_status": props.get("SubState", ""),
                "pid": props.get("MainPID", "0"),
                "uptime": props.get("ActiveEnterTimestamp", "")
            }
        except Exception as e:
            logger.error(f"Failed to get systemctl status for {self.service_name}: {e}")
            return {
                "name": self.service_name,
                "active": False,
                "status": "error",
                "sub_status": str(e),
                "pid": "0",
                "uptime": ""
            }
