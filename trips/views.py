from datetime import datetime

import requests
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import os

from trips.models import Trip


@login_required
def trip_planner(request):
    return render(request, 'trips/trip_planner.html')

@login_required
def view_weather(request, id):
    api_key = os.environ['OPENWEATHER_API_KEY']

    trip = get_object_or_404(Trip, id=id)

    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={trip.latitude}&lon={trip.longitude}&exclude=current,minutely,hourly,alerts&units=imperial&appid={api_key}"
    response = requests.get(url).json()

    processed_days = []

    weather_descriptions = {
        2: ('Storm', 'fa-solid fa-bolt fa-fw'),
        3: ('Drizzle', 'fa-solid fa-cloud-rain fa-fw'),
        5: ('Rain', 'fa-solid fa-cloud-showers-heavy fa-fw'),
        6: ('Snow', 'fa-solid fa-snowflake fa-fw'),
    }

    for day in response['daily']:
        processed_day = {}

        forecast_day = datetime.fromtimestamp(day['dt']).date()

        if forecast_day < trip.start_date:
            continue

        temp = round(day['feels_like']['day'])
        wind_speed = round(day['wind_speed'])
        humidity = round(day['humidity'])
        rain_chance = round(day['pop'] * 100)
        cloud_cover = round(day['clouds'])

        processed_day['day'] = forecast_day.strftime('%a')
        processed_day['date'] = forecast_day.strftime('%b %-d')
        processed_day['temp'] = f'{temp} °F'
        processed_day['wind_speed'] = f'{wind_speed} mph'
        processed_day['humidity'] = f'{humidity}%'
        processed_day['rain_chance'] = f'{rain_chance}%'
        processed_day['cloud_cover'] = f'{cloud_cover}%'

        condition_code = day['weather'][-1]['id']
        condition_group = int(condition_code / 100)
        condition_subgroup = condition_code % 100

        weather_description = weather_descriptions.get(condition_group, 'Clear')

        if condition_group == 8:
            if condition_subgroup == 0:
                weather_description = ('Clear', 'fa-solid fa-sun')
            elif condition_subgroup == 1 or condition_subgroup == 2:
                weather_description = ('Cloudy', 'fa-solid fa-cloud-sun')
            else:
                weather_description = ('Cloudy', 'fa-solid fa-cloud')


        processed_day['description'] = weather_description[0]
        processed_day['icon'] = weather_description[1]

        processed_days.append(processed_day)

    context = {
        'weather': {
            'days': processed_days
        },
        'trip': {
            'destination': trip.destination,
            'start_date': trip.start_date.strftime('%A, %B %-d, %Y'),
            'end_date': trip.end_date.strftime('%A, %B %-d, %Y')
        }
    }

    return render(request, 'trips/view_weather.html', context)
