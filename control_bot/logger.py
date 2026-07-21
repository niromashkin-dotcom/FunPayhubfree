import logging
import sys
import os

def setup_logger(name: str = "ControlBot") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.formatters.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Вывод в консоль
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Вывод в файл
        log_dir = os.path.dirname(os.path.abspath(__file__))
        file_handler = logging.FileHandler(os.path.join(log_dir, "control_bot.log"), encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()
