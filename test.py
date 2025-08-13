#!/usr/bin/env python3
"""
Тестовый файл для проверки исправленного VIN-парсера
"""

import json
from vin_parser import parse_gibdd_response, search_reviews_enhanced, search_board_journals, VINParser

def test_parse_gibdd_response():
    """Тест парсинга ответа ГИБДД"""
    print("🧪 Тест 1: Парсинг ответа ГИБДД...")
    
    # Загружаем тестовые данные
    try:
        with open("gibdd_response.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Тестируем парсинг
        vehicle_info = parse_gibdd_response(data)  # Используем напрямую data, а не data["response"]
        
        if vehicle_info:
            print(f"  ✓ VIN: {vehicle_info.vin}")
            print(f"  ✓ Марка: {vehicle_info.brand}")
            print(f"  ✓ Модель: {vehicle_info.model}")
            print(f"  ✓ Год: {vehicle_info.year}")
            print(f"  ✓ Цвет: {vehicle_info.color}")
            print(f"  ✓ Двигатель: {vehicle_info.engine_volume} / {vehicle_info.power_hp} л.с.")
            print(f"  ✓ История владения: {len(vehicle_info.ownership_history)} записей")
            return vehicle_info
        else:
            print("  ✗ Не удалось распарсить данные")
            return None
            
    except Exception as e:
        print(f"  ✗ Ошибка: {e}")
        return None

def test_search_functions(vehicle_info):
    """Тест функций поиска отзывов и бортжурналов"""
    if not vehicle_info:
        print("🧪 Тест 2 и 3: Пропущены - нет vehicle_info")
        return
    
    print("\n🧪 Тест 2: Поиск отзывов...")
    try:
        reviews_data = {
            "vehicle_info": vehicle_info.to_dict(),  # Преобразуем в словарь
            "max_reviews": 5
        }
        reviews = search_reviews_enhanced(reviews_data)
        print(f"  ✓ Найдено отзывов: {len(reviews)}")
        
        for review in reviews[:2]:  # Показываем первые 2
            print(f"    • {review.get('source')}: {review.get('title', 'Без названия')[:50]}...")
    
    except Exception as e:
        print(f"  ✗ Ошибка при поиске отзывов: {e}")
    
    print("\n🧪 Тест 3: Поиск бортжурналов...")
    try:
        bj_data = {
            "vehicle_info": vehicle_info.to_dict(),  # Преобразуем в словарь
            "max_entries": 5
        }
        journals = search_board_journals(bj_data)
        print(f"  ✓ Найдено бортжурналов: {len(journals)}")
        
        for journal in journals[:2]:  # Показываем первые 2
            print(f"    • {journal.get('source')}: {journal.get('title', 'Без названия')[:50]}...")
    
    except Exception as e:
        print(f"  ✗ Ошибка при поиске бортжурналов: {e}")

def test_full_parser():
    """Тест полного цикла парсера"""
    print("\n🧪 Тест 4: Полный цикл парсера...")
    
    try:
        parser = VINParser()
        vin = "JMBXTGF2WDZ013380"
        
        result = parser.parse_by_vin(
            vin=vin,
            search_reviews=True,
            get_additional=True,
            max_reviews=10,
            use_mock_data=True,
            include_board_journals=True
        )
        
        if result.get("error"):
            print(f"  ✗ Ошибка парсера: {result['error']}")
            return False
        
        print(f"  ✓ VIN обработан: {result['vin']}")
        print(f"  ✓ Источники данных: {result['sources']}")
        print(f"  ✓ Найдено отзывов: {len(result['reviews'])}")
        
        summary = result.get("summary", {})
        if summary:
            print(f"  ✓ Автомобиль: {summary.get('full_name')}")
            print(f"  ✓ Владельцев: {summary.get('owners_count')}")
        
        # Тест экспорта
        print("\n  📄 Тест экспорта отчетов...")
        try:
            html_file = parser.export_report(result, format="html")
            print(f"    ✓ HTML отчет: {html_file}")
        except Exception as e:
            print(f"    ✗ Ошибка экспорта HTML: {e}")
        
        try:
            json_file = parser.export_report(result, format="json")
            print(f"    ✓ JSON отчет: {json_file}")
        except Exception as e:
            print(f"    ✗ Ошибка экспорта JSON: {e}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Критическая ошибка: {e}")
        return False

def test_validation_functions():
    """Тест функций валидации"""
    print("\n🧪 Тест 5: Функции валидации...")
    
    from vin_parser import validate_required_keys, validate_vehicle_info, VehicleInfo
    
    # Тест validate_required_keys
    try:
        data_good = {"vehicle_info": "test", "max_reviews": 10}
        validate_required_keys(data_good, ["vehicle_info"], "test_function")
        print("  ✓ validate_required_keys - корректные данные")
    except Exception as e:
        print(f"  ✗ validate_required_keys - ошибка с корректными данными: {e}")
    
    try:
        data_bad = {"max_reviews": 10}
        validate_required_keys(data_bad, ["vehicle_info"], "test_function")
        print("  ✗ validate_required_keys - должна была выбросить ошибку")
    except ValueError:
        print("  ✓ validate_required_keys - корректно обработала отсутствующие ключи")
    except Exception as e:
        print(f"  ✗ validate_required_keys - неожиданная ошибка: {e}")
    
    # Тест validate_vehicle_info
    vehicle_good = VehicleInfo(vin="TEST", brand="Toyota", model="Camry")
    if validate_vehicle_info(vehicle_good, "test_function"):
        print("  ✓ validate_vehicle_info - корректный объект")
    else:
        print("  ✗ validate_vehicle_info - ошибка с корректным объектом")
    
    if not validate_vehicle_info(None, "test_function"):
        print("  ✓ validate_vehicle_info - корректно обработала None")
    else:
        print("  ✗ validate_vehicle_info - должна была вернуть False для None")

def test_error_handling():
    """Тест обработки ошибок"""
    print("\n🧪 Тест 6: Обработка ошибок...")
    
    parser = VINParser()
    
    # Тест неверного VIN
    result = parser.parse_by_vin("INVALID_VIN")
    if result.get("error"):
        print("  ✓ Корректно обработан неверный VIN")
    else:
        print("  ✗ Не обработан неверный VIN")
    
    # Тест пустых данных ГИБДД
    empty_gibdd_data = {"success": False}
    vehicle_info = parse_gibdd_response(empty_gibdd_data)
    if vehicle_info is None:
        print("  ✓ Корректно обработаны пустые данные ГИБДД")
    else:
        print("  ✗ Не обработаны пустые данные ГИБДД")

def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов исправленного VIN-парсера\n")
    print("=" * 60)
    
    # Тест 1: Парсинг ГИБДД
    vehicle_info = test_parse_gibdd_response()
    
    # Тест 2-3: Поиск отзывов и бортжурналов
    test_search_functions(vehicle_info)
    
    # Тест 4: Полный цикл
    full_test_success = test_full_parser()
    
    # Тест 5: Валидация
    test_validation_functions()
    
    # Тест 6: Обработка ошибок
    test_error_handling()
    
    print("\n" + "=" * 60)
    print("🏁 Тестирование завершено")
    
    if full_test_success:
        print("✅ Основные функции работают корректно")
    else:
        print("❌ Обнаружены критические ошибки")

if __name__ == "__main__":
    run_all_tests()