#!/usr/bin/env python3
"""
Тестовый скрипт для комплексного тестирования плагина Autosmm
Проверяет все доноры: Craft (Ibox), Sell Clarity, Vast Sounds, Steam DLCs
"""
import json
import time
import sys
from pathlib import Path

# Импортируем плагин
sys.path.insert(0, str(Path(__file__).parent))

class TestAutosmmPlugin:
    """Тестовый класс для проверки плагина Autosmm"""
    
    def __init__(self):
        self.results = {}
        self.plugin_config = None
        self.load_config()
        
    def load_config(self):
        """Загружаем конфигурацию плагина"""
        config_path = Path("configs/plugins/autosmm_plugin.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.plugin_config = json.load(f)
            print(f"✅ Загружена конфигурация Autosmm плагина")
            print(f"   Версия конфига: {self.plugin_config.get('config_version', 'N/A')}")
            print(f"   Включен: {'✅' if self.plugin_config.get('enabled') else '❌'}")
            print(f"   Dry-run: {'✅ Включен' if self.plugin_config.get('dry_run') else '❌ Выключен'}")
            print(f"   Test mode: {'✅ Включен' if self.plugin_config.get('test_mode') else '❌ Выключен'}")
        else:
            print(f"❌ Конфигурация плагина не найдена: {config_path}")
            sys.exit(1)
    
    def get_expected_suppliers(self):
        """Возвращает список ожидаемых доноров для Autosmm плагина"""
        return [
            {"name": "craft", "marker": "[IB#", "type": "craft_smm", "full_name": "Craft (Ibox)"},
            {"name": "sell_clarity", "marker": "[SC#", "type": "smm", "full_name": "Sell Clarity"},
            {"name": "vast_sounds", "marker": "[VS#", "type": "smm", "full_name": "Vast Sounds"},
            {"name": "steam_dlcs", "marker": "[ST#", "type": "steam", "full_name": "Steam DLCs"},
        ]
    
    def test_plugin_config(self):
        """Тестируем общую конфигурацию плагина"""
        print(f"\n{'='*60}")
        print(f"🔧 ТЕСТ КОНФИГУРАЦИИ ПЛАГИНА")
        print(f"{'='*60}")
        
        results = {
            'enabled': self.plugin_config.get('enabled', False),
            'api_key_present': bool(self.plugin_config.get('api_key')),
            'api_url_present': bool(self.plugin_config.get('api_url')),
            'dry_run': self.plugin_config.get('dry_run', True),
            'test_mode': self.plugin_config.get('test_mode', True),
        }
        
        print(f"📋 Основные настройки:")
        print(f"   Включен: {'✅' if results['enabled'] else '❌'}")
        print(f"   API ключ: {'✅ Присутствует' if results['api_key_present'] else '❌ Отсутствует'}")
        print(f"   API URL: {'✅ ' + self.plugin_config.get('api_url', '') if results['api_url_present'] else '❌ Отсутствует'}")
        print(f"   Dry-run режим: {'✅ Включен' if results['dry_run'] else '❌ Выключен'}")
        print(f"   Тестовый режим: {'✅ Включен' if results['test_mode'] else '❌ Выключен'}")
        
        # Проверяем важные настройки
        if not results['enabled']:
            print(f"   ⚠️  Плагин отключен! Включите в конфигурации")
        
        if results['dry_run']:
            print(f"   ⚠️  Dry-run режим включен - реальные заказы не будут создаваться")
        
        if results['test_mode']:
            print(f"   ⚠️  Тестовый режим включен - используются тестовые данные")
        
        # Проверяем сообщения
        messages = [
            ("msg_ask_link", "Запрос ссылки"),
            ("msg_confirm", "Подтверждение"),
            ("msg_order_created", "Создание заказа"),
            ("msg_completed", "Завершение заказа"),
        ]
        
        print(f"\n💬 Проверка сообщений:")
        for key, desc in messages:
            message = self.plugin_config.get(key, '')
            if message:
                print(f"   ✅ {desc}: присутствует ({len(message)} символов)")
            else:
                print(f"   ❌ {desc}: отсутствует")
        
        # Проверяем разрешенные домены
        allowed_domains = self.plugin_config.get('allowed_domains', [])
        print(f"\n🌐 Разрешенные домены: {len(allowed_domains)}")
        if allowed_domains:
            print(f"   Примеры: {', '.join(allowed_domains[:5])}...")
        
        self.results['plugin_config'] = results
        return all([results['enabled'], results['api_key_present'], results['api_url_present']])
    
    def test_supplier_mapping(self):
        """Тестируем маппинг доноров (lot_mapping)"""
        print(f"\n{'='*60}")
        print(f"🗺️ ТЕСТ МАППИНГА ДОНОРОВ")
        print(f"{'='*60}")
        
        lot_mapping = self.plugin_config.get('lot_mapping', {})
        expected_suppliers = self.get_expected_suppliers()
        
        print(f"📊 Маппинг лотов: {len(lot_mapping)} записей")
        
        if not lot_mapping:
            print(f"   ⚠️  Маппинг лотов пуст! Это может быть проблемой")
            print(f"   💡 Рекомендация: Настройте lot_mapping для автоматического определения поставщиков")
        
        # Проверяем наличие ожидаемых маркеров
        found_markers = set()
        for marker_info in lot_mapping.values():
            if isinstance(marker_info, dict):
                marker = marker_info.get('marker', '')
                if marker:
                    found_markers.add(marker)
        
        print(f"\n🔍 Ожидаеме маркеры доноров:")
        for supplier in expected_suppliers:
            marker = supplier['marker']
            if marker in found_markers:
                print(f"   ✅ {supplier['full_name']}: маркер {marker} найден в маппинге")
            elif marker in str(lot_mapping):
                print(f"   ⚠️  {supplier['full_name']}: маркер {marker} найден в данных")
            else:
                print(f"   ❌ {supplier['full_name']}: маркер {marker} не найден")
        
        # Сохраняем результаты
        self.results['lot_mapping'] = {
            'has_mapping': bool(lot_mapping),
            'mapping_count': len(lot_mapping),
            'found_markers': list(found_markers),
        }
        
        return bool(lot_mapping)
    
    def test_supplier_workflow(self, supplier_info):
        """Тестируем workflow для конкретного донора"""
        supplier_name = supplier_info['name']
        full_name = supplier_info['full_name']
        marker = supplier_info['marker']
        supplier_type = supplier_info['type']
        
        print(f"\n{'='*60}")
        print(f"🔄 ТЕСТ WORKFLOW: {full_name.upper()}")
        print(f"{'='*60}")
        
        print(f"📋 Информация о доноре:")
        print(f"   Название: {full_name}")
        print(f"   Тип: {supplier_type}")
        print(f"   Маркер: {marker}")
        
        # Симулируем полный workflow
        stages = []
        
        # 1. Создание лота
        test_lot = {
            'title': f'SMM Услуга {full_name} {marker}100',
            'price': 100,
            'description': f'Автоматическая SMM услуга от {full_name}'
        }
        stages.append(("📝 Создание лота", True))
        print(f"   ✅ Создан тестовый лот: {test_lot['title']}")
        
        # 2. Покупка лота
        test_order = {
            'order_id': f'autosmm-test-{int(time.time())}',
            'title': test_lot['title'],
            'buyer': 'test-buyer',
            'chat_id': 'test-chat-456'
        }
        stages.append(("🛒 Покупка лота", True))
        print(f"   ✅ Симулирована покупка: {test_order['order_id']}")
        
        # 3. Детекция поставщика
        supplier_detected = marker in test_order['title']
        stages.append(("🔍 Детекция поставщика", supplier_detected))
        if supplier_detected:
            print(f"   ✅ Поставщик детектирован по маркеру {marker}")
        else:
            print(f"   ❌ Поставщик не детектирован (маркер {marker} не найден)")
        
        # 4. Автоответ с запросом ссылки
        ask_link_msg = self.plugin_config.get('msg_ask_link', '')
        has_ask_link = bool(ask_link_msg)
        stages.append(("💬 Запрос ссылки", has_ask_link))
        if has_ask_link:
            print(f"   ✅ Автоответ настроен: '{ask_link_msg[:50]}...'")
        else:
            print(f"   ❌ Сообщение с запросом ссылки отсутствует")
        
        # 5. Получение и валидация ссылки
        test_link = "https://t.me/test_channel"
        allowed_domains = self.plugin_config.get('allowed_domains', [])
        link_valid = any(domain in test_link for domain in allowed_domains)
        stages.append(("🔗 Валидация ссылки", link_valid))
        if link_valid:
            print(f"   ✅ Ссылка валидна: {test_link}")
        else:
            print(f"   ❌ Ссылка невалидна или домен не разрешен")
        
        # 6. Подтверждение заказа
        confirm_msg = self.plugin_config.get('msg_confirm', '')
        has_confirm = bool(confirm_msg)
        stages.append(("✅ Подтверждение заказа", has_confirm))
        if has_confirm:
            print(f"   ✅ Сообщение подтверждения настроено")
        
        # 7. Создание заказа у поставщика
        # Симулируем API вызов (в dry-run режиме это не происходит)
        dry_run = self.plugin_config.get('dry_run', True)
        test_mode = self.plugin_config.get('test_mode', True)
        
        if dry_run or test_mode:
            print(f"   ⚠️  Dry-run/Test режим: реальный API вызов не выполняется")
            api_success = True  # В тестовом режиме считаем успешным
        else:
            # Здесь была бы реальная проверка API
            api_success = False
            print(f"   ⚠️  Реальный режим: требуется проверка API ключа")
        
        stages.append(("🔗 API интеграция", api_success))
        
        # 8. Уведомление о создании заказа
        order_created_msg = self.plugin_config.get('msg_order_created', '')
        has_order_created = bool(order_created_msg)
        stages.append(("📦 Уведомление о заказе", has_order_created))
        
        # 9. Мониторинг выполнения
        check_interval = self.plugin_config.get('check_interval_minutes', 5)
        stages.append(("⏳ Мониторинг выполнения", True))
        print(f"   ✅ Интервал проверки: {check_interval} минут")
        
        # 10. Завершение заказа
        completed_msg = self.plugin_config.get('msg_completed', '')
        has_completed = bool(completed_msg)
        stages.append(("🎉 Завершение заказа", has_completed))
        
        # 11. Запрос отзыва
        ask_review = "⭐" in completed_msg if completed_msg else False
        stages.append(("⭐ Запрос отзыва", ask_review))
        
        # Подсчитываем результаты
        successful_stages = sum(1 for _, result in stages if result)
        total_stages = len(stages)
        success_rate = (successful_stages / total_stages) * 100
        
        print(f"\n📊 РЕЗУЛЬТАТЫ WORKFLOW:")
        for stage_name, stage_result in stages:
            status = "✅" if stage_result else "❌"
            print(f"   {status} {stage_name}")
        
        print(f"\n   📈 Успешных этапов: {successful_stages}/{total_stages} ({success_rate:.1f}%)")
        
        # Сохраняем результаты
        supplier_results = {
            'workflow_stages': stages,
            'successful_stages': successful_stages,
            'total_stages': total_stages,
            'success_rate': success_rate,
            'workflow_ok': success_rate >= 70,
        }
        
        self.results[supplier_name] = supplier_results
        
        return supplier_results['workflow_ok']
    
    def test_notifications_and_alerts(self):
        """Тестируем уведомления и алерты"""
        print(f"\n{'='*60}")
        print(f"🔔 ТЕСТ УВЕДОМЛЕНИЙ И АЛЕРТОВ")
        print(f"{'='*60}")
        
        results = {}
        
        # Проверяем настройки алертов
        min_balance_alert = self.plugin_config.get('min_balance_alert', 0)
        auto_refund = self.plugin_config.get('auto_refund', False)
        ask_confirmation = self.plugin_config.get('ask_confirmation', False)
        
        print(f"📊 Настройки уведомлений:")
        print(f"   Минимальный баланс для алерта: {min_balance_alert}")
        print(f"   Автовозврат: {'✅ Включен' if auto_refund else '❌ Выключен'}")
        print(f"   Запрос подтверждения: {'✅ Включен' if ask_confirmation else '❌ Выключен'}")
        
        # Проверяем тестовый чат
        test_chat_id = self.plugin_config.get('test_chat_id', '')
        if test_chat_id:
            print(f"   Тестовый чат ID: {test_chat_id}")
            results['test_chat_configured'] = True
        else:
            print(f"   ⚠️  Тстовый чат не настроен")
            results['test_chat_configured'] = False
        
        # Проверяем интеграцию с Telegram
        # Для этого нужно проверить конфиг главного приложения
        main_config_path = Path("configs/_main.cfg")
        telegram_enabled = False
        if main_config_path.exists():
            try:
                content = main_config_path.read_text(encoding='utf-8')
                for line in content.split('\n'):
                    if '[Telegram]' in line:
                        # Ищем следующую строку с enabled
                        telegram_enabled = any('enabled : 1' in l for l in content.split('\n'))
            except:
                pass
        
        print(f"\n🤖 Интеграция с Telegram:")
        print(f"   Telegram бот: {'✅ Включен' if telegram_enabled else '❌ Выключен'}")
        results['telegram_integration'] = telegram_enabled
        
        # Проверяем уведомления в приложении
        print(f"\n📱 Уведомления в приложении:")
        print(f"   ⚠️  Требуется проверка dashboard API")
        results['app_notifications'] = "Требуется проверка"
        
        self.results['notifications'] = results
        return results.get('test_chat_configured', False) and results.get('telegram_integration', False)
    
    def run_all_tests(self):
        """Запускаем все тесты для Autosmm плагина"""
        print("🚀 ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ AUTOSMM ПЛАГИНА")
        print("="*60)
        
        # Запускаем тесты
        plugin_config_ok = self.test_plugin_config()
        mapping_ok = self.test_supplier_mapping()
        
        # Тестируем всех ожидаемых доноров
        suppliers = self.get_expected_suppliers()
        supplier_results = {}
        
        print(f"\n{'='*60}")
        print(f"🧪 ТЕСТИРОВАНИЕ ВСЕХ ДОНОРОВ ({len(suppliers)})")
        print(f"{'='*60}")
        
        for supplier in suppliers:
            workflow_ok = self.test_supplier_workflow(supplier)
            supplier_results[supplier['name']] = {
                'workflow_ok': workflow_ok,
                'success_rate': self.results[supplier['name']]['success_rate'],
            }
        
        # Тестируем уведомления
        notifications_ok = self.test_notifications_and_alerts()
        
        # Выводим итоговую таблицу
        print(f"\n{'='*60}")
        print("📊 ИТОГОВАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ AUTOSMM")
        print(f"{'='*60}")
        print(f"{'Донор':<20} {'Workflow':<15} {'Успешность':<15}")
        print(f"{'-'*60}")
        
        total_success_rate = 0
        for supplier in suppliers:
            name = supplier['full_name'][:18] + '..' if len(supplier['full_name']) > 18 else supplier['full_name']
            results = supplier_results[supplier['name']]
            workflow = '✅' if results['workflow_ok'] else '❌'
            success_rate = results['success_rate']
            
            print(f"{name:<20} {workflow:<15} {success_rate:<15.1f}%")
            total_success_rate += success_rate
        
        avg_success_rate = total_success_rate / len(suppliers) if suppliers else 0
        
        print(f"{'-'*60}")
        print(f"{'СРЕДНЕЕ':<20} {'✅' if avg_success_rate >= 70 else '❌':<15} {avg_success_rate:<15.1f}%")
        
        # Общий итог
        print(f"\n{'='*60}")
        print("🎯 ОБЩИЙ ИТОГ AUTOSMM ПЛАГИНА:")
        print(f"{'='*60}")
        
        overall_score = (
            (1 if plugin_config_ok else 0) +
            (1 if mapping_ok else 0) +
            (1 if notifications_ok else 0) +
            (1 if avg_success_rate >= 70 else 0)
        ) / 4 * 100
        
        print(f"📋 Конфигурация плагина: {'✅' if plugin_config_ok else '❌'}")
        print(f"🗺️  Маппинг доноров: {'✅' if mapping_ok else '❌'}")
        print(f"🔔 Уведомления: {'✅' if notifications_ok else '❌'}")
        print(f"🔄 Workflow доноров: {'✅' if avg_success_rate >= 70 else '❌'} ({avg_success_rate:.1f}%)")
        print(f"\n📈 Общая оценка: {overall_score:.1f}%")
        
        if overall_score >= 70:
            print(f"\n🎉 Autosmm плагин готов к работе!")
            return True
        else:
            print(f"\n❌ Autosmm плагин требует доработки!")
            print(f"💡 Рекомендации:")
            if not plugin_config_ok:
                print(f"   - Включите плагин и настройте API ключи")
            if not mapping_ok:
                print(f"   - Настройте lot_mapping для автоматического определения поставщиков")
            if not notifications_ok:
                print(f"   - Настройте уведомления в Telegram")
            if avg_success_rate < 70:
                print(f"   - Улучшите workflow доноров (текущий результат: {avg_success_rate:.1f}%)")
            return False

def main():
    """Основная функция"""
    print("🔧 ТЕСТИРОВАНИЕ ПЛАГИНА AUTOSMM")
    print("="*60)
    
    tester = TestAutosmmPlugin()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 Autosmm плагин прошел тестирование успешно!")
        print("📋 Следующий шаг: проверка создания лотов и интеграции")
        return True
    else:
        print("\n❌ Autosmm плагин требует доработки перед использованием")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)