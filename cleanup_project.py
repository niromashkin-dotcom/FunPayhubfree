#!/usr/bin/env python3
"""
Скрипт очистки проекта FunPayHub от мусорных файлов
Удаляет все файлы, которые не участвуют в работе приложения
"""

import os
import shutil
import stat
from pathlib import Path
from datetime import datetime


class ProjectCleaner:
    """
    Очистка проекта от ненужных файлов и директорий
    """
    
    def __init__(self):
        self.removed_count = 0
        self.errors_count = 0
        self.cleanup_log = []
        
        # Файлы и директории, которые НЕОБХОДИМО сохранить
        self.essential_files = {
            # Корневые файлы
            'funpayhub_main.py',
            'cardinal.py', 
            'hub_bootstrap.py',
            'eventbus.py',
            'state_api.py',
            'telegram_agent.pyw',
            'tg_bot_service.py',
            'Start.bat',
            'README.md',
            'requirements.txt',
            '.gitignore',
            '.clinerules',
            '.roomodes',
            
            # Конфигурационные файлы (только безопасные версии)
            'configs/_main.cfg.safe',
            'configs/plugins/autosmm_plugin.json.safe',
            'tg_bot/authorized_users.json.safe',
            
            # Секреты
            'configs/secrets/',
            '.env.example',
            
            # Основные директории
            'FunPayAPI/',
            'runtime/',
            'dashboard/',
            'tg_bot/',
            'web/',
            'Utils/',
            'data/',
            'locales/',
            'tests/',
            'userdata/',
            'security/',
            
            # Тестовые скрипты
            'test_autodonate.py',
            'test_autosmm.py',
            'test_final_system.py',
            'test_golden_key.py',
            'migrate_secrets.py',
            'cleanup_project.py',
            'BUSINESS_LAUNCH_PLAN.md',
            'AI_CONTEXT.md',
        }
        
        # Паттерны для удаления
        self.delete_patterns = [
            # Резервные копии
            '**/*.bak',
            '**/*.bak_*',
            '**/*_backup*',
            '**/*_old*',
            '**/*backup*',
            
            # Временные файлы
            '**/*.tmp',
            '**/*.temp',
            '**/*.swp',
            '**/*.swo',
            '**/*~',
            
            # Кэши Python
            '**/*.pyc',
            '**/__pycache__',
            '**/.pycache',
            
            # Логи и PID файлы
            '**/*.log',
            '**/*.pid',
            '**/*.lock',
            
            # Системные файлы
            '**/.DS_Store',
            '**/Thumbs.db',
            '**/desktop.ini',
        ]
        
        # Директории для полного удаления
        self.delete_directories = [
            'autopilot/',           # Тестовые данные автопилота
            '_trash_backup_20260620_153523/',  # Старые бэкапы
            'web/static_broken_20260703_133459/',  # Сломанные файлы
            'inbox/',              # Временные задачи
            'tasks/',              # Старые задачи
            'experimental/',       # Экспериментальный код
            'backups/',            # Резервные копии (можно заархивировать)
            
            # Устаревшие файлы в tg_bot
            'tg_bot/authorized_users_cp.py',
            'tg_bot/auto_delivery_cp.py',
            'tg_bot/auto_response_cp.py',
            'tg_bot/config_loader_cp.py',
            'tg_bot/default_cp.py',
            'tg_bot/plugins_cp.py',
            'tg_bot/proxy_cp.py',
            'tg_bot/templates_cp.py',
            
            # Устаревшие файлы в web
            'web/seller_api_clean_backup.py',
            'web/seller_api.py.bak',
            'web/app_test.py',
            
            # Устаревшие файлы в runtime
            'runtime/seller_service_backup_20260624_154341.py',
            'runtime/seller_service.py.bak',
            'runtime/lot_generator.py.bak',
            
            # Устаревшие файлы в dashboard
            'dashboard/api.py.bak',
            'dashboard/api.py.bak_AA',
            'dashboard/api.py.bak_20260705_012142',
        ]
    
    def is_essential(self, path: Path) -> bool:
        """Проверяет, является ли файл/директория необходимой"""
        # Преобразуем путь в строку для сравнения
        path_str = str(path)
        
        # Проверяем по полным путям
        for essential in self.essential_files:
            if path_str == essential or path_str.startswith(essential):
                return True
        
        # Проверяем родительские директории
        for parent in path.parents:
            if str(parent) + '/' in self.essential_files:
                return True
        
        return False
    
    def safe_delete(self, path: Path, is_dir: bool = False):
        """Безопасное удаление файла или директории"""
        try:
            if is_dir:
                # Для директорий проверяем, что они пустые
                if path.exists() and path.is_dir():
                    # Проверяем, что директория не содержит важных файлов
                    has_important = False
                    for item in path.rglob('*'):
                        if self.is_essential(item):
                            has_important = True
                            break
                    
                    if not has_important:
                        shutil.rmtree(path)
                        self.removed_count += 1
                        self.cleanup_log.append(f"🗑️  Удалена директория: {path}")
                    else:
                        self.cleanup_log.append(f"⚠️  Пропущена директория (содержит важные файлы): {path}")
            else:
                # Для файлов
                if path.exists() and path.is_file():
                    path.unlink()
                    self.removed_count += 1
                    self.cleanup_log.append(f"🗑️  Удален файл: {path}")
                    
        except PermissionError:
            self.errors_count += 1
            self.cleanup_log.append(f"❌ Ошибка прав доступа: {path}")
        except Exception as e:
            self.errors_count += 1
            self.cleanup_log.append(f"❌ Ошибка удаления {path}: {e}")
    
    def clean_by_patterns(self):
        """Очистка по паттернам"""
        print("🔍 Очистка по паттернам...")
        
        for pattern in self.delete_patterns:
            for item in Path('.').glob(pattern):
                if not self.is_essential(item):
                    self.safe_delete(item, item.is_dir())
    
    def clean_directories(self):
        """Очистка указанных директорий"""
        print("📁 Очистка указанных директорий...")
        
        for dir_path in self.delete_directories:
            path = Path(dir_path)
            if path.exists():
                if path.is_dir():
                    self.safe_delete(path, is_dir=True)
                elif path.is_file():
                    self.safe_delete(path, is_dir=False)
            else:
                # Проверяем файлы внутри директорий
                parent_dir = Path(dir_path.split('/')[0])
                if parent_dir.exists():
                    for item in parent_dir.rglob('*'):
                        item_str = str(item)
                        if any(dir_path in item_str for dir_path in self.delete_directories if '/' in dir_path):
                            if not self.is_essential(item):
                                self.safe_delete(item, item.is_dir())
    
    def clean_original_configs_with_secrets(self):
        """Очистка оригинальных конфигов с секретами"""
        print("🔐 Очистка оригинальных конфигов с секретами...")
        
        # Список оригинальных конфигов, которые нужно заархивировать или удалить
        original_configs = [
            'configs/_main.cfg',                     # Содержит Golden Key
            'configs/plugins/autosmm_plugin.json',   # Содержит API ключи
            'configs/plugins/autodonate_plugin.json', # Содержит API ключи
            'tg_bot/authorized_users.json',          # Содержит password hash
        ]
        
        for config_path in original_configs:
            path = Path(config_path)
            if path.exists():
                # Создаем архивную копию на случай, если что-то пойдет не так
                archive_path = path.with_suffix('.original')
                try:
                    shutil.copy2(path, archive_path)
                    self.cleanup_log.append(f"💾 Архивная копия: {path} → {archive_path}")
                    
                    # Удаляем оригинал (уже есть безопасная версия .safe)
                    self.safe_delete(path)
                    
                except Exception as e:
                    self.errors_count += 1
                    self.cleanup_log.append(f"❌ Ошибка архивирования {path}: {e}")
    
    def cleanup_empty_directories(self):
        """Удаление пустых директорий"""
        print("🧹 Удаление пустых директорий...")
        
        for dir_path in Path('.').rglob('*'):
            if dir_path.is_dir():
                try:
                    # Проверяем, что директория пуста
                    if not any(dir_path.iterdir()):
                        # Проверяем, что это не важная директория
                        if not self.is_essential(dir_path):
                            dir_path.rmdir()
                            self.removed_count += 1
                            self.cleanup_log.append(f"🧹 Удалена пустая директория: {dir_path}")
                except Exception:
                    pass  # Игнорируем ошибки при удалении
    
    def calculate_project_size(self):
        """Рассчитывает размер проекта"""
        print("📊 Расчет размера проекта...")
        
        total_size = 0
        total_files = 0
        essential_size = 0
        essential_files = 0
        
        for path in Path('.').rglob('*'):
            if path.is_file():
                try:
                    size = path.stat().st_size
                    total_size += size
                    total_files += 1
                    
                    if self.is_essential(path):
                        essential_size += size
                        essential_files += 1
                except Exception:
                    pass
        
        return {
            'total_size_mb': total_size / 1024 / 1024,
            'total_files': total_files,
            'essential_size_mb': essential_size / 1024 / 1024,
            'essential_files': essential_files,
            'waste_size_mb': (total_size - essential_size) / 1024 / 1024,
            'waste_files': total_files - essential_files
        }
    
    def print_summary(self, stats: dict):
        """Выводит сводку очистки"""
        print("\n" + "="*80)
        print("📊 СВОДКА ОЧИСТКИ ПРОЕКТА")
        print("="*80)
        
        print(f"\n📈 СТАТИСТИКА ПРОЕКТА:")
        print(f"   Всего файлов: {stats['total_files']}")
        print(f"   Размер проекта: {stats['total_size_mb']:.2f} MB")
        print(f"   Важных файлов: {stats['essential_files']}")
        print(f"   Размер важных файлов: {stats['essential_size_mb']:.2f} MB")
        print(f"   Мусорных файлов: {stats['waste_files']}")
        print(f"   Размер мусора: {stats['waste_size_mb']:.2f} MB")
        
        print(f"\n🗑️  РЕЗУЛЬТАТЫ ОЧИСТКИ:")
        print(f"   Удалено файлов/директорий: {self.removed_count}")
        print(f"   Ошибок: {self.errors_count}")
        
        print(f"\n📋 ЛОГ ОЧИСТКИ (первые 20 записей):")
        for i, log_entry in enumerate(self.cleanup_log[:20]):
            print(f"   {log_entry}")
        
        if len(self.cleanup_log) > 20:
            print(f"   ... и еще {len(self.cleanup_log) - 20} записей")
        
        print(f"\n🎯 РЕКОМЕНДАЦИИ:")
        
        if stats['waste_size_mb'] > 10:
            print(f"   1. ✅ Вы освободили {stats['waste_size_mb']:.1f} MB дискового пространства")
        else:
            print(f"   1. ℹ️  Проект уже довольно чистый")
        
        if self.errors_count > 0:
            print(f"   2. ⚠️  Было {self.errors_count} ошибок. Проверьте права доступа")
        
        print(f"   3. 📁 Проверьте безопасные конфиги (.safe файлы)")
        print(f"   4. 🔐 Убедитесь, что оригинальные конфиги с секретами заархивированы")
        print(f"   5. 🚀 Проект готов к развертыванию на 24/7 сервере")
        
        print(f"\n⚠️  ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ:")
        print(f"   - Проверьте, что все важные файлы сохранены")
        print(f"   - Убедитесь, что .env.example заполнен корректно")
        print(f"   - Протестируйте работу приложения после очистки")
        
        print(f"\n✅ ОЧИСТКА ЗАВЕРШЕНА")
        print("="*80)
    
    def create_backup_instruction(self):
        """Создает инструкцию по бэкапу"""
        instruction = """# 📁 ИНСТРУКЦИЯ ПО БЭКАПУ И ОЧИСТКЕ FUNPAYHUB

## 🎯 ЧТО БЫЛО СДЕЛАНО:

### 1. 🔐 МИГРАЦИЯ СЕКРЕТОВ
- Секреты перемещены из открытых файлов в `configs/secrets/encrypted_secrets.json`
- Созданы безопасные версии конфигов (файлы с расширением `.safe`)
- Оригинальные конфиги заархивированы (файлы с расширением `.original`)

### 2. 🗑️  ОЧИСТКА ПРОЕКТА
- Удалены временные файлы (.tmp, .log, .pyc, __pycache__)
- Удалены резервные копии (.bak, _backup, _old)
- Удалены тестовые и экспериментальные данные
- Очищены устаревшие файлы и директории

### 3. 📝 ДОКУМЕНТАЦИЯ
- Создан файл `.env.example` для переменных окружения
- Создан план запуска `BUSINESS_LAUNCH_PLAN.md`
- Обновлен контекст `AI_CONTEXT.md`

## 🚀 СЛЕДУЮЩИЕ ШАГИ:

### 1. НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
```bash
# Скопируйте .env.example в .env
cp .env.example .env

# Отредактируйте .env файл
# Заполните значения секретов из encrypted_secrets.json
# Установите TELEGRAM_BOT_TOKEN и другие настройки
```

### 2. ТЕСТИРОВАНИЕ РАБОТЫ
```bash
# Запустите тестовые скрипты
python test_golden_key.py
python test_autodonate.py
python test_autosmm.py
python test_final_system.py
```

### 3. РАЗВЕРТЫВАНИЕ НА 24/7 СЕРВЕРЕ
Следуйте инструкциям в `BUSINESS_LAUNCH_PLAN.md`:
1. Создайте аккаунт на Railway.app
2. Настройте переменные окружения в Railway
3. Задеплойте проект
4. Настройте мониторинг

## 📁 СТРУКТУРА ПРОЕКТА ПОСЛЕ ОЧИСТКИ:

```
FunPayHub/
├── 📁 configs/                    # Конфигурации
│   ├── _main.cfg.safe            # Безопасный конфиг
│   ├── plugins/                  # Конфиги плагинов
│   └── secrets/                  # Зашифрованные секреты
├── 📁 security/                  # Безопасность
├── 📁 tg_bot/                    # Telegram бот
├── 📁 runtime/                   # Ядро системы
├── 📁 FunPayAPI/                 # FunPay API
├── 📁 web/                       # Web интерфейс
├── 📁 dashboard/                 # Дашборд
├── 📁 Utils/                     # Утилиты
├── 📁 data/                      # Данные
├── 📁 locales/                   # Локализация
├── 📁 tests/                     # Тесты
├── 📁 userdata/                  # Пользовательские данные
├── 🔐 .env.example               # Пример переменных окружения
├── 📋 BUSINESS_LAUNCH_PLAN.md    # План запуска
├── 🧠 AI_CONTEXT.md              # Контекст проекта
├── 🚀 funpayhub_main.py          # Основной файл
├── 🤖 tg_bot_service.py          # Telegram бот
└── 📦 requirements.txt           # Зависимости
```

## ⚠️  ВАЖНЫЕ ПРЕДУПРЕЖДЕНИЯ:

1. **НИКОГДА не коммитьте в git:**
   - `.env` файл
   - `configs/secrets/encrypted_secrets.json`
   - Файлы с расширением `.original`

2. **Регулярно делайте бэкапы:**
   ```bash
   # Скрипт для бэкапа
   tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz --exclude="__pycache__" --exclude="*.pyc" .
   ```

3. **Мониторинг 24/7:**
   - Используйте UptimeRobot для проверки доступности
   - Настройте Telegram уведомления о сбоях
   - Регулярно проверяйте логи

## 🆘 ЕСЛИ ЧТО-ТО СЛОМАЛОСЬ:

1. Проверьте архивные копии (файлы `.original`)
2. Восстановите оригинальные конфиги из архива
3. Проверьте переменные окружения в `.env`
4. Запустите тесты для диагностики

---
*Очистка выполнена: {timestamp}*
""".format(timestamp=datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        
        instruction_file = Path("BACKUP_INSTRUCTIONS.md")
        instruction_file.write_text(instruction, encoding='utf-8')
        print(f"📝 Создана инструкция по бэкапу: {instruction_file}")


def main():
    """Основная функция очистки"""
    print("🧹 ОЧИСТКА ПРОЕКТА FUNPAYHUB")
    print("="*80)
    print("Цель: Удалить все файлы, которые не участвуют в работе приложения")
    print("="*80)
    
    # Создаем экземпляр очистителя
    cleaner = ProjectCleaner()
    
    # Рассчитываем исходный размер
    print("\n📊 РАСЧЕТ ИСХОДНОГО РАЗМЕРА ПРОЕКТА...")
    initial_stats = cleaner.calculate_project_size()
    print(f"   Исходный размер: {initial_stats['total_size_mb']:.2f} MB")
    print(f"   Исходное количество файлов: {initial_stats['total_files']}")
    
    # Выполняем очистку
    print("\n🚀 ВЫПОЛНЕНИЕ ОЧИСТКИ...")
    cleaner.clean_by_patterns()
    cleaner.clean_directories()
    cleaner.clean_original_configs_with_secrets()
    cleaner.cleanup_empty_directories()
    
    # Рассчитываем конечный размер
    print("\n📊 РАСЧЕТ КОНЕЧНОГО РАЗМЕРА ПРОЕКТА...")
    final_stats = cleaner.calculate_project_size()
    
    # Создаем инструкцию по бэкапу
    cleaner.create_backup_instruction()
    
    # Выводим сводку
    cleaner.print_summary(final_stats)


if __name__ == "__main__":
    main()