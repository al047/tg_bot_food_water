import re
import logging
import requests
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_food_info_openfoodfacts(food_name):
    try:
        search_url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            'search_terms': food_name,
            'search_simple': 1,
            'action': 'process',
            'json': 1,
            'page_size': 3  # Увеличим количество результатов
        }

        print(f"=== ЗАПРОС К OPENFOODFACTS API ===")
        print(f"Продукт: {food_name}")
        print(f"URL: {search_url}")
        print(f"Параметры: {params}")

        response = requests.get(search_url, params=params, timeout=10)

        print(f"Статус ответа: {response.status_code}")
        print(f"=== КОНЕЦ ЗАПРОСА ===")

        if response.status_code != 200:
            return None, None, None

        data = response.json()
        products_count = len(data.get('products', []))
        print(f"Найдено продуктов: {products_count}")

        if products_count == 0:
            return None, None, None

        product = data['products'][0]
        product_name = product.get('product_name', food_name)
        brand = product.get('brands', '')

        calories = product.get('nutriments', {}).get('energy-kcal_100g')

        if not calories:
            energy_kj = product.get('nutriments', {}).get('energy-kj_100g')
            if energy_kj:
                calories = energy_kj / 4.184

        print(f"Бренд: {brand}")
        print(f"Название: {product_name}")
        print(f"Калории: {calories} ккал/100г")

        return calories, product_name, 100

    except Exception as e:
        print(f"Ошибка OpenFoodFacts: {e}")
        return None, None, None


def search_food_products(food_name, limit=3):
    """Ищет продукты через OpenFoodFacts API"""
    try:
        search_url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            'search_terms': food_name,
            'search_simple': 1,
            'action': 'process',
            'json': 1,
            'page_size': limit
        }

        print(f"Поиск продуктов OpenFoodFacts: {food_name}")
        response = requests.get(search_url, params=params, timeout=5)

        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code}")
            return []

        data = response.json()
        products = data.get('products', [])

        print(f"Найдено продуктов: {len(products)}")

        results = []
        for product in products[:limit]:
            name = product.get('product_name', 'Неизвестно')
            brand = product.get('brands', '')
            calories = product.get('nutriments', {}).get('energy-kcal_100g')

            if brand:
                display_name = f"{brand} - {name}"
            else:
                display_name = name

            results.append({
                'name': display_name,
                'calories': calories,
                'id': product.get('code')
            })

        return results

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []
