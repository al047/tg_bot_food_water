import logging
import requests
import sys
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.ext import MessageHandler, filters
from dotenv import load_dotenv
load_dotenv()


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не установлен!")
    sys.exit(1)


try:
    from utils.calculations import calculate_water_norm, calculate_calories_norm, get_temperature
    from utils.food_api import get_food_info_openfoodfacts, get_average_calories
except ImportError:
    def calculate_water_norm(weight, activity, city):
        base = weight * 30
        activity_water = (activity // 30) * 500
        temp = get_temperature(city) if 'get_temperature' in globals() else 20
        weather_water = 500 if temp and temp > 25 else 0
        return int(base + activity_water + weather_water)

    def calculate_calories_norm(weight, height, age, activity):
        base = 10 * weight + 6.25 * height - 5 * age
        activity_factor = 1.2 + (activity / 60) * 0.1
        daily_calories = base * activity_factor
        activity_calories = activity * 7
        return daily_calories + activity_calories

    def get_temperature(city):
        """функция получения температуры из OpenWeatherMap"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            logger.error("OPENWEATHER_API_KEY не установлен в .env файле!")
            return None

        try:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': api_key,
                'units': 'metric',  # градусы Цельсия
                'lang': 'ru'
            }

            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                temp = data['main']['temp']
                logger.info(f"Получена температура для {city}: {temp}°C")
                return temp
            else:
                logger.error(
                    f"Ошибка API OpenWeatherMap: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error(" Таймаут при запросе погоды")
            return None
        except Exception as e:
            logger.error(f" Ошибка получения температуры: {e}")
            return None

    def get_food_info_openfoodfacts(food):
        calories = get_average_calories(food)
        return (calories, food, 100)

    def get_average_calories(food):
        calories_db = {
            'яблоко': 52, 'банан': 89, 'гречка': 132, 'курица': 165,
            'рис': 130, 'хлеб': 265, 'молоко': 42, 'йогурт': 59,
            'яйцо': 155, 'рыба': 206, 'говядина': 250, 'картофель': 77
        }
        return calories_db.get(food.lower(), 250)

users = {}
WEIGHT, HEIGHT, AGE, ACTIVITY, CITY = range(5)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для расчета норм воды и калорий.\n"
        "Используйте /help для списка команд"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Основные команды:
/set_profile - Настроить профиль
/profile - Показать данные профиля
/log_water <количество> - Записать выпитую воду (в мл)
/log_food <продукт> - Записать съеденную еду 
/log_workout <тип> <время> - Записать тренировку
/check_progress - Проверить прогресс
/weather - Погода 
/food_search - Поиск продукта 

Примеры:
/log_water 500
/log_food банан
/log_workout бег 30
"""
    await update.message.reply_text(help_text)


async def set_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Настройка профиля. Введите ваш вес в кг:")
    return WEIGHT


async def weight_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        context.user_data['weight'] = weight
        await update.message.reply_text("Введите ваш рост в см:")
        return HEIGHT
    except ValueError:
        await update.message.reply_text("Введите число (например: 70)")
        return WEIGHT


async def height_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = float(update.message.text)
        context.user_data['height'] = height
        await update.message.reply_text("Введите ваш возраст:")
        return AGE
    except ValueError:
        await update.message.reply_text("Введите число (например: 175)")
        return HEIGHT


async def age_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        context.user_data['age'] = age
        await update.message.reply_text("Сколько минут активности у вас в день?")
        return ACTIVITY
    except ValueError:
        await update.message.reply_text("Введите целое число (например: 30)")
        return AGE


async def activity_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        activity = float(update.message.text)
        context.user_data['activity'] = activity
        await update.message.reply_text("В каком городе вы находитесь?")
        return CITY
    except ValueError:
        await update.message.reply_text("Введите число (например: 45)")
        return ACTIVITY


async def city_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    user_id = update.effective_user.id

    users[user_id] = {
        "weight": context.user_data['weight'],
        "height": context.user_data['height'],
        "age": context.user_data['age'],
        "activity": context.user_data['activity'],
        "city": city,
        "water_goal": 0,
        "calorie_goal": 0,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0
    }

    users[user_id]['water_goal'] = calculate_water_norm(
        users[user_id]['weight'],
        users[user_id]['activity'],
        users[user_id]['city']
    )

    users[user_id]['calorie_goal'] = calculate_calories_norm(
        users[user_id]['weight'],
        users[user_id]['height'],
        users[user_id]['age'],
        users[user_id]['activity']
    )

    response = f"""
Профиль сохранен.

Ваши нормы:
Вода: {users[user_id]['water_goal']} мл/день
Калории: {users[user_id]['calorie_goal']:.0f} ккал/день
"""
    await update.message.reply_text(response)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Настройка профиля отменена.")
    return ConversationHandler.END


async def log_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль: /set_profile")
        return

    if not context.args:
        await update.message.reply_text("Использование: /log_water <количество в мл>")
        return

    try:
        water_amount = float(context.args[0])
        users[user_id]['logged_water'] += water_amount

        remaining = users[user_id]['water_goal'] - \
            users[user_id]['logged_water']

        await update.message.reply_text(
            f"Записано: {water_amount} мл воды\n"
            f"Выпито всего: {users[user_id]['logged_water']} мл\n"
            f"Осталось до цели: {remaining if remaining > 0 else 0} мл"
        )
    except ValueError:
        await update.message.reply_text("Введите число (например: /log_water 500)")


async def log_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль: /set_profile")
        return

    if not context.args:
        await update.message.reply_text("Использование: /log_food <продукт> <граммы>")
        await update.message.reply_text("Пример: /log_food банан 150")
        return

    # Если первым аргументом число - используем результаты поиска
    if len(context.args) >= 2 and context.args[0].isdigit():
        try:
            product_num = int(context.args[0]) - 1
            weight_grams = float(context.args[1])

            search_results = context.user_data.get('search_results', [])
            if not search_results or product_num >= len(search_results):
                await update.message.reply_text("Сначала выполните поиск: /food_search <продукт>")
                return

            product = search_results[product_num]
            calories_per_100g = product['calories'] or get_average_calories(
                product['name'])
            product_name = product['name']

            calories = (calories_per_100g / 100) * weight_grams
            users[user_id]['logged_calories'] += calories

            await update.message.reply_text(
                f"Записано из базы OpenFoodFacts!\n"
                f"{product_name}\n"
                f"{weight_grams}г = {calories:.1f} ккал"
            )
            return

        except ValueError:
            await update.message.reply_text("Используйте: /log_food <номер> <граммы>")
            return

    # Обычный режим
    food_name = ' '.join(context.args[:-1])
    try:
        weight_grams = float(context.args[-1])

        await update.message.reply_text(f"Ищу '{food_name}' в базе OpenFoodFacts...")

        calories_per_100g, product_name, _ = get_food_info_openfoodfacts(
            food_name)

        if not calories_per_100g:
            calories_per_100g = get_average_calories(food_name)
            product_name = food_name
            source = "(среднее значение)"
        else:
            source = "(данные из базы OpenFoodFacts)"

        calories = (calories_per_100g / 100) * weight_grams
        users[user_id]['logged_calories'] += calories

        await update.message.reply_text(
            f"Записано!\n"
            f"{product_name} {source}\n"
            f"{weight_grams}г = {calories:.1f} ккал\n"
            f"Калорийность: {calories_per_100g} ккал/100г"
        )

    except ValueError:
        await update.message.reply_text("Используйте: /log_food <продукт> <граммы>")
    except IndexError:
        await update.message.reply_text("Используйте: /log_food <продукт> <граммы>")


async def food_weight_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight_grams = float(update.message.text)
        user_id = update.effective_user.id

        food_data = context.user_data.get('pending_food')
        if not food_data:
            await update.message.reply_text("Ошибка: данные о продукте не найдены")
            return ConversationHandler.END

        calories = (food_data['calories_per_100g'] / 100) * weight_grams

        users[user_id]['logged_calories'] += calories

        await update.message.reply_text(f"Записано: {calories:.1f} ккал.")

        context.user_data.pop('pending_food', None)

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Введите число (например: 150)")
        return 'WAITING_FOOD_WEIGHT'


async def log_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль: /set_profile")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Использование: /log_workout <тип> <время в минутах>")
        return

    workout_type = context.args[0]
    try:
        minutes = float(context.args[1])

        workout_calories = {
            'бег': 10, 'ходьба': 5, 'плавание': 8,
            'велосипед': 7, 'тренажерный': 6, 'йога': 4
        }

        calories_per_min = workout_calories.get(workout_type.lower(), 5)
        burned = calories_per_min * minutes
        water_additional = (minutes // 30) * 200

        users[user_id]['burned_calories'] += burned
        users[user_id]['water_goal'] += water_additional

        await update.message.reply_text(
            f"{workout_type} {minutes} минут\n"
            f"Сожжено: {burned:.0f} ккал\n"
            f"Выпейте дополнительно {water_additional} мл воды"
        )
    except ValueError:
        await update.message.reply_text("Время должно быть числом")


async def check_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль: /set_profile")
        return

    user = users[user_id]
    water_remaining = max(0, user['water_goal'] - user['logged_water'])
    calorie_balance = user['logged_calories'] - user['burned_calories']

    progress_text = f"""
Прогресс:

Вода:
- Выпито: {user['logged_water']} мл из {user['water_goal']} мл
- Осталось: {water_remaining} мл

Калории:
- Потреблено: {user['logged_calories']} ккал
- Сожжено: {user['burned_calories']} ккал
- Баланс: {calorie_balance:.0f} ккал
"""

    if 'calorie_goal' in user:
        progress_text += f"- Цель: {user['calorie_goal']} ккал\n"

    await update.message.reply_text(progress_text)


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /weather <город>")
        return

    city = ' '.join(context.args)

    # Получаем температуру
    temp = get_temperature(city)

    if temp is not None:
        response = f"Температура в {city}: {temp}°C"

        if temp > 25:
            response += "\nЖаркая погода! Пейте больше воды."
        elif temp < 10:
            response += "\nХолодно! Тепло одевайтесь."
    else:
        response = f"Не удалось получить температуру для {city}"

    await update.message.reply_text(response)


async def food_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /food_search <название продукта>")
        return

    food_name = ' '.join(context.args)

    from utils.food_api import search_food_products
    results = search_food_products(food_name, limit=5)

    if not results:
        await update.message.reply_text(f"Продукты '{food_name}' не найдены в базе OpenFoodFacts")
        return

    response = f"Найдено в базе OpenFoodFacts:\n\n"
    for i, product in enumerate(results, 1):
        calories = product['calories'] or "неизвестно"
        response += f"{i}. {product['name']}\n"
        response += f"   Калории: {calories} ккал/100г\n\n"

    response += "Используйте: /log_food <номер> <граммы>"

    context.user_data['search_results'] = results

    await update.message.reply_text(response)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать данные профиля пользователя"""
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Профиль не найден. Сначала настройте профиль: /set_profile")
        return

    user = users[user_id]

    profile_text = f"""
 ВАШ ПРОФИЛЬ

Основные данные:
 Вес: {user['weight']} кг
 Рост: {user['height']} см
 Возраст: {user['age']} лет
 Активность: {user['activity']} мин/день
 Город: {user['city']}

Дневные нормы:
 Вода: {user['water_goal']} мл/день
 Калории: {user['calorie_goal']:.0f} ккал/день

Сегодняшний прогресс:
 Выпито воды: {user['logged_water']} мл
 Потреблено калорий: {user['logged_calories']:.1f} ккал
 Сожжено калорий: {user['burned_calories']:.1f} ккал

Осталось сегодня:
 Воды: {max(0, user['water_goal'] - user['logged_water'])} мл
 Калорий: {user['calorie_goal'] - user['logged_calories'] + user['burned_calories']:.0f} ккал до цели
"""

    await update.message.reply_text(profile_text)


async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        logger.info(f"Получено сообщение: {update.message.text}")
    return True


def main():
    application = Application.builder().token(TOKEN).build()

    conv_profile = ConversationHandler(
        entry_points=[CommandHandler('set_profile', set_profile)],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_received)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_received)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_received)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity_received)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    conv_food = ConversationHandler(
        entry_points=[CommandHandler('log_food', log_food)],
        states={
            'WAITING_FOOD_WEIGHT': [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               food_weight_received)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(MessageHandler(
        filters.TEXT, log_message), group=-1)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_profile)
    application.add_handler(conv_food)
    application.add_handler(CommandHandler("log_water", log_water))
    application.add_handler(CommandHandler("log_workout", log_workout))
    application.add_handler(CommandHandler("check_progress", check_progress))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("food_search", food_search))
    application.add_handler(CommandHandler("profile", profile_command))

    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()
