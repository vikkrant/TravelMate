from datetime import datetime

import requests
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
import os
from django.contrib import messages

from trips.models import Trip


@login_required
def trip_planner(request):
    if request.method == 'POST':
        destination = request.POST.get('destination')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # For now, we'll use default coordinates. In a real app, you'd want to geocode the destination
        latitude = 0.0
        longitude = 0.0
        
        try:
            trip = Trip.objects.create(
                user=request.user,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                latitude=latitude,
                longitude=longitude
            )
            messages.success(request, 'Trip created successfully!')
            return redirect('my_trips')
        except Exception as e:
            messages.error(request, f'Error creating trip: {str(e)}')
    
    return render(request, 'trips/trip_planner.html')

@login_required
def my_trips(request):
    trips = Trip.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'trips/my_trips.html', {'trips': trips})

@login_required
def view_weather(request, id):
    api_key = os.environ['OPENWEATHER_API_KEY']

    trip = get_object_or_404(Trip, id=id)

    # Using the 2.5 version of the API which is more stable
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={trip.latitude}&lon={trip.longitude}&units=imperial&appid={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        weather_data = response.json()
        
        if 'list' not in weather_data:
            raise ValueError("Unexpected API response format")

        processed_days = []
        current_date = None
        daily_data = {}

        # Process the 3-hour forecast data into daily data
        for forecast in weather_data['list']:
            forecast_time = datetime.fromtimestamp(forecast['dt'])
            forecast_date = forecast_time.date()
            
            if forecast_date < trip.start_date:
                continue
                
            if forecast_date > trip.end_date:
                break

            if current_date != forecast_date:
                if current_date is not None:
                    processed_days.append(daily_data)
                current_date = forecast_date
                daily_data = {
                    'day': forecast_time.strftime('%a'),
                    'date': forecast_time.strftime('%b %d').lstrip('0'),
                    'temp': f"{round(forecast['main']['feels_like'])} °F",
                    'wind_speed': f"{round(forecast['wind']['speed'])} mph",
                    'humidity': f"{round(forecast['main']['humidity'])}%",
                    'rain_chance': f"{round(forecast.get('pop', 0) * 100)}%",
                    'cloud_cover': f"{round(forecast['clouds']['all'])}%",
                    'description': forecast['weather'][0]['main'],
                    'icon': get_weather_icon(forecast['weather'][0]['id'])
                }
            else:
                # Update with the latest data for the day
                daily_data.update({
                    'temp': f"{round(forecast['main']['feels_like'])} °F",
                    'wind_speed': f"{round(forecast['wind']['speed'])} mph",
                    'humidity': f"{round(forecast['main']['humidity'])}%",
                    'rain_chance': f"{round(forecast.get('pop', 0) * 100)}%",
                    'cloud_cover': f"{round(forecast['clouds']['all'])}%",
                    'description': forecast['weather'][0]['main'],
                    'icon': get_weather_icon(forecast['weather'][0]['id'])
                })

        if daily_data:
            processed_days.append(daily_data)

        context = {
            'weather': {
                'days': processed_days,
                'error': None
            },
            'trip': {
                'destination': trip.destination,
                'start_date': trip.start_date.strftime('%A, %B %d, %Y').lstrip('0'),
                'end_date': trip.end_date.strftime('%A, %B %d, %Y').lstrip('0')
            }
        }

    except requests.exceptions.RequestException as e:
        context = {
            'weather': {
                'days': [],
                'error': 'Failed to fetch weather data. Please try again later.'
            },
            'trip': {
                'destination': trip.destination,
                'start_date': trip.start_date.strftime('%A, %B %d, %Y').lstrip('0'),
                'end_date': trip.end_date.strftime('%A, %B %d, %Y').lstrip('0')
            }
        }
    except (KeyError, ValueError) as e:
        context = {
            'weather': {
                'days': [],
                'error': 'Error processing weather data.'
            },
            'trip': {
                'destination': trip.destination,
                'start_date': trip.start_date.strftime('%A, %B %d, %Y').lstrip('0'),
                'end_date': trip.end_date.strftime('%A, %B %d, %Y').lstrip('0')
            }
        }

    return render(request, 'trips/view_weather.html', context)

def get_weather_icon(weather_id):
    weather_descriptions = {
        2: 'fa-solid fa-bolt fa-fw',  # Thunderstorm
        3: 'fa-solid fa-cloud-rain fa-fw',  # Drizzle
        5: 'fa-solid fa-cloud-showers-heavy fa-fw',  # Rain
        6: 'fa-solid fa-snowflake fa-fw',  # Snow
        7: 'fa-solid fa-smog fa-fw',  # Atmosphere
        8: 'fa-solid fa-cloud fa-fw',  # Clouds
    }
    
    condition_group = int(weather_id / 100)
    if condition_group == 8:
        if weather_id % 100 == 0:
            return 'fa-solid fa-sun fa-fw'
        elif weather_id % 100 in [1, 2]:
            return 'fa-solid fa-cloud-sun fa-fw'
        else:
            return 'fa-solid fa-cloud fa-fw'
    
    return weather_descriptions.get(condition_group, 'fa-solid fa-sun fa-fw')

@login_required
def edit_trip(request, id):
    trip = get_object_or_404(Trip, id=id, user=request.user)
    
    if request.method == 'POST':
        destination = request.POST.get('destination')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            trip.destination = destination
            trip.start_date = start_date
            trip.end_date = end_date
            trip.save()
            messages.success(request, 'Trip updated successfully!')
            return redirect('trips:my_trips')
        except Exception as e:
            messages.error(request, f'Error updating trip: {str(e)}')
    
    return render(request, 'trips/edit_trip.html', {'trip': trip})

@login_required
def delete_trip(request, id):
    trip = get_object_or_404(Trip, id=id, user=request.user)
    
    if request.method == 'POST':
        try:
            trip.delete()
            messages.success(request, 'Trip deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting trip: {str(e)}')
        return redirect('trips:my_trips')
    
    return render(request, 'trips/delete_trip.html', {'trip': trip})
