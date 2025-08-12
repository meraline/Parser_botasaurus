"""
VIN-парсер с API ГИБДД и автоматическим поиском отзывов
Получает официальные данные из ГИБДД и собирает отзывы по модели
"""

from botasaurus.browser import browser, Driver
from botasaurus.request import request, Request
from botasaurus.soupify import soupify
from botasaurus import bt
from botasaurus.cache import Cache
from typing import Dict, List, Optional, Tuple
import re
import time
import json
from datetime import datetime
from dataclasses import dataclass, asdict

# ==================== МОДЕЛЬ ДАННЫХ ====================

@dataclass
class VehicleInfo:
    """Структура данных автомобиля"""
    vin: str
    brand: str = None
    model: str = None
    year: int = None
    engine_volume: str = None
    power_hp: str = None
    power_kwt: str = None
    color: str = None
    body_number: str = None
    engine_number: str = None
    category: str = None
    type_info: str = None
    pts_number: str = None
    pts_issue: str = None
    ownership_history: List[Dict] = None
    technical_specs: Dict = None
    reviews: List[Dict] = None


# ==================== УТИЛИТЫ ====================

def validate_required_keys(data: Dict, required_keys: List[str], func_name: str) -> None:
    """Validate that all required keys exist in the provided data dict.

    Args:
        data: Input dictionary passed to a browser-decorated function.
        required_keys: Keys that must be present in ``data``.
        func_name: Name of the function for clearer error messages.

    Raises:
        ValueError: If any of the required keys are missing.
    """
    missing = [key for key in required_keys if key not in data or data[key] is None]
    if missing:
        missing_keys = ", ".join(missing)
        raise ValueError(f"Missing required keys for {func_name}: {missing_keys}")

# ==================== API ГИБДД ====================

@request(
    cache=True,
    max_retry=5
)
def get_gibdd_data(request: Request, vin: str, api_key: str = None) -> Dict:
    """
    Получение данных из API ГИБДД
    
    Args:
        vin: VIN-код автомобиля
        api_key: API ключ для доступа к сервису (если требуется)
    """
    
    try:
        # Здесь должен быть ваш реальный endpoint API
        # Это пример структуры запроса
        api_url = "https://api.your-service.ru/gibdd"  # Замените на реальный URL
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        payload = {
            "vin": vin.upper(),
            "method": "gibdd"
        }
        
        response = request.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка API: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Ошибка при запросе к API ГИБДД: {e}")
        return None

def parse_gibdd_response(gibdd_data: Dict) -> VehicleInfo:
    """
    Парсинг ответа от API ГИБДД в структуру VehicleInfo
    """
    
    if not gibdd_data or not gibdd_data.get('success'):
        return None
    
    response = gibdd_data.get('response', {})
    vehicle = response.get('vehicle', {})
    passport = response.get('vehiclePassport', {})
    ownership = response.get('ownershipPeriod', [])
    
    # Извлекаем марку и модель из полного названия
    full_model = vehicle.get('model', '')
    brand = None
    model = None
    
    # Парсим название модели (например: "МИЦУБИСИ АУТЛЕНДЕР 2.0")
    model_parts = full_model.strip().split()
    if model_parts:
        # Преобразуем марки в нормальный вид
        brand_mapping = {
            'МИЦУБИСИ': 'Mitsubishi',
            'МИТСУБИСИ': 'Mitsubishi',
            'ТОЙОТА': 'Toyota',
            'НИССАН': 'Nissan',
            'МАЗДА': 'Mazda',
            'ХОНДА': 'Honda',
            'ФОЛЬКСВАГЕН': 'Volkswagen',
            'БМВ': 'BMW',
            'МЕРСЕДЕС': 'Mercedes-Benz',
            'АУДИ': 'Audi',
            'ШКОДА': 'Skoda',
            'РЕНО': 'Renault',
            'ПЕЖО': 'Peugeot',
            'СИТРОЕН': 'Citroen',
            'ФОРД': 'Ford',
            'ШЕВРОЛЕ': 'Chevrolet',
            'КИА': 'Kia',
            'ХЕНДАЙ': 'Hyundai',
            'ХУНДАЙ': 'Hyundai',
            'ЛАДА': 'Lada',
            'ВАЗ': 'VAZ'
        }
        
        brand_raw = model_parts[0].upper()
        brand = brand_mapping.get(brand_raw, model_parts[0].capitalize())
        
        # Модель - все остальное кроме марки и объема двигателя
        model_parts_clean = []
        for part in model_parts[1:]:
            # Пропускаем числа с точкой (объем двигателя)
            if not re.match(r'^\d+\.\d+$', part):
                model_parts_clean.append(part.capitalize())
        model = ' '.join(model_parts_clean) if model_parts_clean else model_parts[1] if len(model_parts) > 1 else None
    
    # Преобразуем историю владения
    ownership_history = []
    for period in ownership:
        ownership_entry = {
            'type': period.get('simplePersonTypeInfo', ''),
            'from': period.get('from', ''),
            'to': period.get('to', ''),
            'period': period.get('period', ''),
            'operation': period.get('lastOperationInfo', '')
        }
        ownership_history.append(ownership_entry)
    
    # Создаем объект VehicleInfo
    vehicle_info = VehicleInfo(
        vin=vehicle.get('vin', ''),
        brand=brand,
        model=model,
        year=int(vehicle.get('year', 0)) if vehicle.get('year') else None,
        engine_volume=vehicle.get('engineVolume', ''),
        power_hp=vehicle.get('powerHp', ''),
        power_kwt=vehicle.get('powerKwt', ''),
        color=vehicle.get('color', ''),
        body_number=vehicle.get('bodyNumber', ''),
        engine_number=vehicle.get('engineNumber', ''),
        category=vehicle.get('category', ''),
        type_info=vehicle.get('typeinfo', ''),
        pts_number=passport.get('number', ''),
        pts_issue=passport.get('issue', ''),
        ownership_history=ownership_history,
        technical_specs={
            'engine_volume': vehicle.get('engineVolume', ''),
            'power_hp': vehicle.get('powerHp', ''),
            'power_kwt': vehicle.get('powerKwt', ''),
            'category': vehicle.get('category', ''),
            'type': vehicle.get('typeinfo', '')
        }
    )
    
    return vehicle_info

# ==================== ДОПОЛНИТЕЛЬНЫЕ ИСТОЧНИКИ ДАННЫХ ====================

@browser(
    block_images=True,
    cache=True,
    reuse_driver=True,
    max_retry=3
)
def get_additional_info(driver: Driver, data: Dict) -> Dict:
    """Placeholder for fetching additional vehicle information.

    Currently no external sources are queried.
    """
    return {}

# ==================== ПОИСК ОТЗЫВОВ ====================

@browser(
    block_images=False,
    cache=True,
    reuse_driver=True,
    max_retry=3
)
def search_reviews_enhanced(driver: Driver, data: Dict) -> List[Dict]:

    """Улучшенный поиск отзывов с учетом данных из ГИБДД"""

    vehicle_info: VehicleInfo = data["vehicle_info"]
    max_reviews: int = data.get("max_reviews", 20)


    reviews = []

    if not vehicle_info.brand or not vehicle_info.model:
        print("  ⚠️ Недостаточно данных для поиска отзывов")
        return reviews
    
    # Нормализуем названия для URL
    brand_normalized = vehicle_info.brand.lower().replace(' ', '-').replace('_', '-')
    model_normalized = vehicle_info.model.lower().replace(' ', '-').replace('_', '-')
    
    # Специальная обработка для некоторых брендов
    brand_url_mapping = {
        'mitsubishi': 'mitsubishi',
        'volkswagen': 'volkswagen',
        'mercedes-benz': 'mercedes',
        'bmw': 'bmw',
        'toyota': 'toyota',
        'nissan': 'nissan',
        'mazda': 'mazda',
        'honda': 'honda',
        'hyundai': 'hyundai',
        'kia': 'kia',
        'ford': 'ford',
        'chevrolet': 'chevrolet',
        'lada': 'lada',
        'vaz': 'vaz'
    }
    
    brand_for_url = brand_url_mapping.get(brand_normalized, brand_normalized)
    
    # Специальная обработка моделей
    model_url_mapping = {
        'outlander': 'outlander',
        'asx': 'asx',
        'pajero': 'pajero',
        'lancer': 'lancer',
        'eclipse cross': 'eclipse-cross',
        'l200': 'l200'
    }
    
    model_for_url = model_url_mapping.get(model_normalized, model_normalized)
    
    print(f"\n🔍 Поиск отзывов для {vehicle_info.brand} {vehicle_info.model} {vehicle_info.year}")
    
    # === DROM.RU ===
    try:
        print("  📋 Поиск на Drom.ru...")
        drom_url = f"https://www.drom.ru/reviews/{brand_for_url}/{model_for_url}/"
        
        driver.google_get(drom_url, bypass_cloudflare=True)
        driver.sleep(2)
        
        # Если страница не найдена, пробуем альтернативный URL
        if driver.select('.error-page'):
            # Пробуем поиск
            search_url = f"https://www.drom.ru/reviews/search/?text={vehicle_info.brand}+{vehicle_info.model}"
            driver.get_via_this_page(search_url)
            driver.sleep(2)
        
        # Фильтр по году если возможно
        if vehicle_info.year:
            year_links = driver.select_all(f'a[href*="{vehicle_info.year}"]')
            if year_links:
                year_links[0].click()
                driver.sleep(2)
        
        # Собираем карточки отзывов
        review_cards = driver.select_all('.css-1ksh4lf')[:max_reviews//2]
        
        for card in review_cards:
            review_data = {
                "source": "drom.ru",
                "brand": vehicle_info.brand,
                "model": vehicle_info.model,
                "year": vehicle_info.year,
                "vin_checked": True
            }
            
            # Заголовок
            title_elem = card.select('h3')
            if title_elem:
                review_data['title'] = title_elem.get_text(strip=True)
            
            # Ссылка
            link_elem = card.select('a')
            if link_elem:
                href = link_elem.get_attribute('href')
                if href and not href.startswith('http'):
                    href = f"https://www.drom.ru{href}"
                review_data['url'] = href
            
            # Рейтинг
            rating_elem = card.select('.css-kxziuu')
            if rating_elem:
                review_data['rating'] = rating_elem.get_text(strip=True)
            
            # Информация об авто в отзыве
            specs_elem = card.select('.css-1x4jntm')
            if specs_elem:
                specs_text = specs_elem.get_text(strip=True)
                # Проверяем соответствие характеристикам
                if vehicle_info.engine_volume:
                    engine_vol_clean = vehicle_info.engine_volume.replace('.0', '').replace(',', '.')
                    if engine_vol_clean in specs_text:
                        review_data['engine_match'] = True
            
            # Краткое описание
            desc_elem = card.select('.css-1wdvlz0')
            if desc_elem:
                review_data['preview'] = desc_elem.get_text(strip=True)[:200]
            
            reviews.append(review_data)
        
        print(f"    ✓ Найдено {len(reviews)} отзывов на Drom.ru")
        
    except Exception as e:
        print(f"    ✗ Ошибка при поиске на Drom.ru: {e}")
    
    # === DRIVE2.RU ===
    try:
        print("  🚗 Поиск на Drive2.ru...")
        
        # Специальные URL для Drive2
        drive2_brand_mapping = {
            'mitsubishi': 'mitsubishi',
            'volkswagen': 'volkswagen',
            'mercedes-benz': 'mercedes-benz',
            'toyota': 'toyota',
            'nissan': 'nissan',
            'mazda': 'mazda',
            'honda': 'honda'
        }
        
        drive2_brand = drive2_brand_mapping.get(brand_normalized, brand_for_url)
        drive2_url = f"https://www.drive2.ru/experience/{drive2_brand}/{model_for_url}/"
        
        driver.get_via_this_page(drive2_url)
        driver.sleep(2)
        
        # Если не найдено, используем поиск
        if driver.select('.c-error'):
            search_url = f"https://www.drive2.ru/search/?q={vehicle_info.brand}+{vehicle_info.model}+{vehicle_info.year}"
            driver.get_via_this_page(search_url)
            driver.sleep(2)
        
        # Собираем карточки
        drive2_cards = driver.select_all('.c-car-card')[:max_reviews//2]
        
        for card in drive2_cards:
            review_data = {
                "source": "drive2.ru",
                "brand": vehicle_info.brand,
                "model": vehicle_info.model,
                "year": vehicle_info.year,
                "vin_checked": True
            }
            
            # Заголовок и ссылка
            title_elem = card.select('.c-car-card__caption a')
            if title_elem:
                review_data['title'] = title_elem.get_text(strip=True)
                href = title_elem.get_attribute('href')
                if href and not href.startswith('http'):
                    href = f"https://www.drive2.ru{href}"
                review_data['url'] = href
            
            # Информация об авто
            info_elem = card.select('.c-car-card__info')
            if info_elem:
                info_text = info_elem.get_text(strip=True)
                review_data['car_info'] = info_text
                
                # Проверяем год
                if vehicle_info.year and str(vehicle_info.year) in info_text:
                    review_data['year_match'] = True
                
                # Проверяем двигатель
                if vehicle_info.engine_volume:
                    engine_vol_clean = vehicle_info.engine_volume.replace('.0', '').replace(',', '.')
                    if engine_vol_clean in info_text:
                        review_data['engine_match'] = True
            
            # Автор
            author_elem = card.select('.c-username__link')
            if author_elem:
                review_data['author'] = author_elem.get_text(strip=True)
            
            # Пробег
            mileage_elem = card.select('.c-car-card__param_mileage')
            if mileage_elem:
                review_data['mileage'] = mileage_elem.get_text(strip=True)
            
            reviews.append(review_data)
        
        print(f"    ✓ Найдено {len([r for r in reviews if r['source'] == 'drive2.ru'])} отзывов на Drive2.ru")
        
    except Exception as e:
        print(f"    ✗ Ошибка при поиске на Drive2.ru: {e}")
    
    # Сортируем отзывы по релевантности
    # Приоритет отзывам с совпадающим годом и двигателем
    for review in reviews:
        relevance_score = 0
        if review.get('year_match'):
            relevance_score += 2
        if review.get('engine_match'):
            relevance_score += 1
        review['relevance_score'] = relevance_score
    
    reviews.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return reviews[:max_reviews]

# ==================== ГЛАВНЫЙ КЛАСС VIN-ПАРСЕРА ====================

class VINParser:
    """Основной класс для парсинга по VIN с использованием API ГИБДД"""
    
    def __init__(self, api_key: str = None):
        """
        Инициализация парсера
        
        Args:
            api_key: API ключ для доступа к сервису ГИБДД
        """
        self.api_key = api_key
    
    @staticmethod
    def validate_vin(vin: str) -> bool:
        """Проверка валидности VIN-кода"""
        vin_pattern = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
        return bool(vin_pattern.match(vin.upper()))
    
    def parse_by_vin(
        self,
        vin: str,
        search_reviews: bool = True,
        max_reviews: int = 20,
        use_mock_data: bool = False
    ) -> Dict:
        """
        Главная функция парсинга по VIN
        
        Args:
            vin: VIN-код автомобиля
            search_reviews: Искать ли отзывы
            max_reviews: Максимальное количество отзывов
            use_mock_data: Использовать тестовые данные (для демонстрации)
        """
        
        # Валидация и нормализация VIN
        vin = vin.upper().strip()
        
        if not self.validate_vin(vin):
            return {
                "error": "Неверный формат VIN-кода",
                "vin": vin
            }
        
        print(f"\n{'='*70}")
        print(f"🔎 КОМПЛЕКСНЫЙ АНАЛИЗ VIN: {vin}")
        print(f"{'='*70}")
        
        result = {
            "vin": vin,
            "parsed_at": datetime.now().isoformat(),
            "sources": [],
            "gibdd_data": None,
            "vehicle_info": None,
            "additional_info": {},
            "reviews": [],
            "summary": {}
        }
        
        # 1. Получение данных из ГИБДД
        print("\n📊 Этап 1: Получение официальных данных ГИБДД...")
        
        if use_mock_data:
            # Используем предоставленные тестовые данные
            gibdd_response = {
                "status": 200,
                "response": {
                    "status": 200,
                    "found": True,
                    "vehicle": {
                        "vin": vin,
                        "bodyNumber": vin,
                        "engineNumber": "9459",
                        "model": "МИЦУБИСИ АУТЛЕНДЕР 2.0",
                        "color": "Белый",
                        "year": "2013",
                        "engineVolume": "1998.0",
                        "powerHp": "146.0",
                        "powerKwt": "107.4",
                        "category": "В",
                        "type": "21",
                        "typeinfo": "Легковые автомобили универсал"
                    },
                    "vehiclePassport": {
                        "number": "78УТ410971",
                        "issue": "ТАМОЖНЯ: 10009194"
                    },
                    "ownershipPeriod": [
                        {
                            "lastOperation": "07",
                            "lastOperationInfo": "прекращение регистрации",
                            "simplePersonType": "Natural",
                            "simplePersonTypeInfo": "Физическое лицо",
                            "from": "19.10.2013",
                            "to": "2024-07-20",
                            "period": "10 лет 9 месяцев"
                        },
                        {
                            "lastOperation": "02",
                            "lastOperationInfo": "регистрация",
                            "simplePersonType": "Natural",
                            "simplePersonTypeInfo": "Физическое лицо",
                            "from": "03.08.2024",
                            "to": "null",
                            "period": "текущий владелец"
                        }
                    ]
                },
                "success": True
            }
        else:
            gibdd_response = get_gibdd_data(vin, self.api_key)
        
        if gibdd_response and gibdd_response.get('success'):
            result["gibdd_data"] = gibdd_response.get('response')
            result["sources"].append("ГИБДД")
            
            # Парсим данные ГИБДД
            vehicle_info = parse_gibdd_response(gibdd_response)
            result["vehicle_info"] = vehicle_info
            
            print(f"  ✓ Получены официальные данные:")
            print(f"    • Марка: {vehicle_info.brand}")
            print(f"    • Модель: {vehicle_info.model}")
            print(f"    • Год: {vehicle_info.year}")
            print(f"    • Цвет: {vehicle_info.color}")
            print(f"    • Двигатель: {vehicle_info.engine_volume} см³, {vehicle_info.power_hp} л.с.")
            print(f"    • ПТС: {vehicle_info.pts_number}")
            print(f"    • Владельцев: {len(vehicle_info.ownership_history)}")
        else:
            print("  ✗ Не удалось получить данные из ГИБДД")
            return result
        
        # 2. Поиск отзывов
        if search_reviews and vehicle_info:
            print("\n📝 Этап 2: Поиск отзывов владельцев...")

            reviews_data = {
                "vehicle_info": vehicle_info,
                "max_reviews": max_reviews,
            }
            validate_required_keys(reviews_data, ["vehicle_info"], "search_reviews_enhanced")
            reviews = search_reviews_enhanced(reviews_data)

            result["reviews"] = reviews
            
            # Статистика по отзывам
            drom_count = len([r for r in reviews if r['source'] == 'drom.ru'])
            drive2_count = len([r for r in reviews if r['source'] == 'drive2.ru'])
            
            print(f"\n  📊 Статистика отзывов:")
            print(f"    • Всего найдено: {len(reviews)}")
            print(f"    • Drom.ru: {drom_count}")
            print(f"    • Drive2.ru: {drive2_count}")
            
            # Отзывы с точным совпадением
            exact_matches = [r for r in reviews if r.get('year_match') or r.get('engine_match')]
            if exact_matches:
                print(f"    • С точным совпадением характеристик: {len(exact_matches)}")
        
        # 3. Формирование итогового резюме
        if vehicle_info:
            result["summary"] = {
                "vin": vin,
                "full_name": f"{vehicle_info.brand} {vehicle_info.model} {vehicle_info.year}",
                "brand": vehicle_info.brand,
                "model": vehicle_info.model,
                "year": vehicle_info.year,
                "color": vehicle_info.color,
                "engine": f"{vehicle_info.engine_volume} см³ / {vehicle_info.power_hp} л.с.",
                "body_type": vehicle_info.type_info,
                "pts": vehicle_info.pts_number,
                "owners_count": len(vehicle_info.ownership_history),
                "current_owner_since": vehicle_info.ownership_history[-1]['from'] if vehicle_info.ownership_history else None,
                "reviews_found": len(result["reviews"]),
                "data_sources": result["sources"],
                "additional_info": {
                    "accidents": result["additional_info"].get("accidents", "Нет данных"),
                    "mileage": result["additional_info"].get("mileage", "Нет данных"),
                    "restrictions": result["additional_info"].get("restrictions", "Нет данных")
                }
            }
        
        print(f"\n{'='*70}")
        print(f"✅ АНАЛИЗ ЗАВЕРШЕН")
        print(f"{'='*70}")
        
        return result
    
    def export_report(self, result: Dict, format: str = "html") -> str:
        """
        Экспорт отчета в различных форматах
        
        Args:
            result: Результат парсинга
            format: Формат экспорта (html, excel, json, pdf)
        """
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vin_report_{result['vin']}_{timestamp}"
        
        if format == "html":
            # Создаем красивый HTML отчет
            html_content = self._generate_html_report(result)
            bt.write_html(html_content, filename)
            return f"{filename}.html"
            
        elif format == "excel":
            # Экспорт в Excel с несколькими листами
            # Основная информация
            main_data = [{
                "VIN": result["vin"],
                "Марка": result["summary"]["brand"],
                "Модель": result["summary"]["model"],
                "Год": result["summary"]["year"],
                "Цвет": result["summary"]["color"],
                "Двигатель": result["summary"]["engine"],
                "Кузов": result["summary"]["body_type"],
                "ПТС": result["summary"]["pts"],
                "Владельцев": result["summary"]["owners_count"],
                "Текущий владелец с": result["summary"]["current_owner_since"],
                "ДТП": result["summary"]["additional_info"]["accidents"],
                "Пробег": result["summary"]["additional_info"]["mileage"],
                "Ограничения": result["summary"]["additional_info"]["restrictions"]
            }]
            
            # Сохраняем в Excel
            bt.write_excel(main_data, filename)
            
            # Сохраняем отзывы отдельно
            if result.get("reviews"):
                reviews_filename = f"reviews_{result['vin']}_{timestamp}"
                bt.write_excel(result["reviews"], reviews_filename)
            
            return f"{filename}.xlsx"
            
        elif format == "json":
            bt.write_json(result, filename)
            return f"{filename}.json"
        
        else:
            raise ValueError(f"Неподдерживаемый формат: {format}")
    
    def _generate_html_report(self, result: Dict) -> str:
        """Генерация HTML отчета"""
        
        summary = result.get("summary", {})
        vehicle_info = result.get("vehicle_info")
        reviews = result.get("reviews", [])
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Отчет по VIN: {result['vin']}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }}
                .section {{
                    background: white;
                    border-radius: 10px;
                    padding: 25px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                }}
                .info-item {{
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }}
                .info-label {{
                    font-size: 12px;
                    color: #666;
                    text-transform: uppercase;
                    margin-bottom: 5px;
                }}
                .info-value {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                }}
                .ownership-timeline {{
                    position: relative;
                    padding-left: 30px;
                }}
                .ownership-item {{
                    position: relative;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    margin-bottom: 15px;
                }}
                .ownership-item:before {{
                    content: '';
                    position: absolute;
                    left: -22px;
                    top: 20px;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: #667eea;
                }}
                .review-card {{
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    transition: transform 0.2s;
                }}
                .review-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}
                .badge {{
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-right: 5px;
                }}
                .badge-success {{
                    background: #d4edda;
                    color: #155724;
                }}
                .badge-warning {{
                    background: #fff3cd;
                    color: #856404;
                }}
                .badge-info {{
                    background: #d1ecf1;
                    color: #0c5460;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{summary.get('full_name', 'Автомобиль')}</h1>
                <p>VIN: {result['vin']}</p>
                <p>Отчет сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            </div>
            
            <div class="section">
                <h2>📊 Основная информация</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Марка и модель</div>
                        <div class="info-value">{summary.get('brand', 'Н/Д')} {summary.get('model', '')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Год выпуска</div>
                        <div class="info-value">{summary.get('year', 'Н/Д')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Цвет</div>
                        <div class="info-value">{summary.get('color', 'Н/Д')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Двигатель</div>
                        <div class="info-value">{summary.get('engine', 'Н/Д')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Тип кузова</div>
                        <div class="info-value">{summary.get('body_type', 'Н/Д')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">ПТС</div>
                        <div class="info-value">{summary.get('pts', 'Н/Д')}</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🚗 Дополнительная информация</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">ДТП</div>
                        <div class="info-value">{summary.get('additional_info', {}).get('accidents', 'Нет данных')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Пробег</div>
                        <div class="info-value">{summary.get('additional_info', {}).get('mileage', 'Нет данных')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Ограничения</div>
                        <div class="info-value">{summary.get('additional_info', {}).get('restrictions', 'Нет данных')}</div>
                    </div>
                </div>
            </div>
        """
        
        # История владения
        if vehicle_info and vehicle_info.ownership_history:
            html += """
            <div class="section">
                <h2>👥 История владения</h2>
                <div class="ownership-timeline">
            """
            
            for i, owner in enumerate(vehicle_info.ownership_history, 1):
                current = owner.get('to') == 'null' or not owner.get('to')
                html += f"""
                    <div class="ownership-item">
                        <h4>Владелец #{i} {' (Текущий)' if current else ''}</h4>
                        <p><strong>Тип:</strong> {owner.get('type', 'Н/Д')}</p>
                        <p><strong>Период:</strong> с {owner.get('from', 'Н/Д')} 
                           {f"по {owner.get('to')}" if not current else 'по настоящее время'}</p>
                        <p><strong>Срок владения:</strong> {owner.get('period', 'Н/Д')}</p>
                        <p><strong>Операция:</strong> {owner.get('operation', 'Н/Д')}</p>
                    </div>
                """
            
            html += """
                </div>
            </div>
            """
        
        # Отзывы
        if reviews:
            html += f"""
            <div class="section">
                <h2>📝 Отзывы владельцев ({len(reviews)} найдено)</h2>
            """
            
            for review in reviews[:10]:  # Показываем первые 10 отзывов
                badges = []
                if review.get('year_match'):
                    badges.append('<span class="badge badge-success">Год совпадает</span>')
                if review.get('engine_match'):
                    badges.append('<span class="badge badge-info">Двигатель совпадает</span>')
                
                source_badge = f'<span class="badge badge-warning">{review["source"]}</span>'
                
                html += f"""
                    <div class="review-card">
                        <div style="margin-bottom: 10px;">
                            {source_badge}
                            {''.join(badges)}
                        </div>
                        <h4>{review.get('title', 'Без названия')}</h4>
                        <p><strong>Рейтинг:</strong> {review.get('rating', 'Н/Д')}</p>
                        {f'<p><strong>Автор:</strong> {review.get("author")}</p>' if review.get("author") else ''}
                        {f'<p><strong>Информация об авто:</strong> {review.get("car_info")}</p>' if review.get("car_info") else ''}
                        {f'<p>{review.get("preview")}</p>' if review.get("preview") else ''}
                        <a href="{review.get('url', '#')}" target="_blank">Читать полностью →</a>
                    </div>
                """
            
            html += """
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html

# ==================== ФУНКЦИИ ДЛЯ УДОБНОЙ РАБОТЫ ====================

def parse_vin_simple(vin: str, api_key: str = None) -> Dict:
    """
    Простая функция для быстрого парсинга VIN
    
    Args:
        vin: VIN-код автомобиля
        api_key: API ключ для ГИБДД (опционально)
    
    Returns:
        Полная информация об автомобиле
    """
    parser = VINParser(api_key=api_key)
    return parser.parse_by_vin(vin, use_mock_data=True)  # Используем mock для демонстрации

def parse_multiple_vins(vin_list: List[str], api_key: str = None, output_format: str = "excel") -> List[Dict]:
    """
    Парсинг нескольких VIN-кодов
    
    Args:
        vin_list: Список VIN-кодов
        api_key: API ключ для ГИБДД
        output_format: Формат сохранения результатов
    """
    parser = VINParser(api_key=api_key)
    results = []
    total = len(vin_list)
    
    print(f"\n🚀 Начинаем парсинг {total} VIN-кодов...")
    
    for idx, vin in enumerate(vin_list, 1):
        print(f"\n[{idx}/{total}] Обработка VIN: {vin}")
        result = parser.parse_by_vin(vin, use_mock_data=True)
        results.append(result)
        
        # Экспорт отчета
        if not result.get("error"):
            parser.export_report(result, format="html")
        
        # Задержка между запросами
        if idx < total:
            time.sleep(2)
    
    # Сохранение общих результатов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "excel":
        # Подготовка данных для Excel
        export_data = []
        for result in results:
            if not result.get("error"):
                summary = result.get("summary", {})
                export_data.append({
                    "VIN": result["vin"],
                    "Автомобиль": summary.get("full_name", ""),
                    "Год": summary.get("year", ""),
                    "Цвет": summary.get("color", ""),
                    "Двигатель": summary.get("engine", ""),
                    "Владельцев": summary.get("owners_count", 0),
                    "Отзывов найдено": summary.get("reviews_found", 0),
                    "ДТП": summary.get("additional_info", {}).get("accidents", ""),
                    "Пробег": summary.get("additional_info", {}).get("mileage", "")
                })
        
        filename = f"vin_batch_results_{timestamp}"
        bt.write_excel(export_data, filename)
        print(f"\n✅ Результаты сохранены в {filename}.xlsx")
    
    # Статистика
    print(f"\n📊 Статистика обработки:")
    print(f"  Всего VIN обработано: {total}")
    print(f"  Успешно: {len([r for r in results if not r.get('error')])}")
    print(f"  С ошибками: {len([r for r in results if r.get('error')])}")
    
    total_reviews = sum(r.get('summary', {}).get('reviews_found', 0) for r in results if not r.get('error'))
    print(f"  Всего найдено отзывов: {total_reviews}")
    
    return results

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def main():
    """Интерактивный интерфейс для работы с VIN-парсером"""
    
    print("\n" + "="*70)
    print("🚗 VIN-ПАРСЕР С ДАННЫМИ ГИБДД И ОТЗЫВАМИ")
    print("="*70)
    print("\nПарсер использует:")
    print("  ✓ Официальные данные ГИБДД")
    print("  ✓ Отзывы с Drom.ru и Drive2.ru")
    
    # Пример использования
    test_vin = "JMBXTGF2WDZ013380"
    
    print(f"\n📋 Демонстрация работы с VIN: {test_vin}")
    
    # Создаем парсер
    parser = VINParser()
    
    # Парсим VIN
    result = parser.parse_by_vin(
        vin=test_vin,
        search_reviews=True,
        max_reviews=20,
        use_mock_data=True  # Используем тестовые данные для демонстрации
    )
    
    # Экспортируем отчет
    if not result.get("error"):
        html_file = parser.export_report(result, format="html")
        excel_file = parser.export_report(result, format="excel")
        json_file = parser.export_report(result, format="json")
        
        print(f"\n📁 Отчеты сохранены:")
        print(f"  • HTML: {html_file}")
        print(f"  • Excel: {excel_file}")
        print(f"  • JSON: {json_file}")
    
    print("\n✅ Готово!")

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    main()
                