import requests
import os

from dotenv import load_dotenv
load_dotenv()


def calculate_water_norm(weight, activity_minutes, city):
    base = weight * 30
    activity_water = (activity_minutes // 30) * 500

    temp = get_temperature(city)
    weather_water = 0
    if temp and temp > 25:
        weather_water = 500

    total_water = base + activity_water + weather_water
    return int(total_water)


def calculate_calories_norm(weight, height, age, activity_minutes):
    bmr = 10 * weight + 6.25 * height - 5 * age
    activity_factor = 1.2 + (activity_minutes / 60) * 0.1
    daily_calories = bmr * activity_factor
    activity_calories = activity_minutes * 7

    return daily_calories + activity_calories


def get_temperature(city):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return None

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            return data['main']['temp']
    except:
        pass

    return None
