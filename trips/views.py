from datetime import datetime
import json
import requests
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
import os
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
import openai
from django.utils import timezone
from .models import OutfitRecommendation, OutfitItem

from trips.models import Trip, PackingListItem

def send_api_fail_email(api_name):
    admin_users = User.objects.filter(is_staff=True)

    # Get emails of all users who are staff or superusers
    admin_emails = [user.email for user in list(admin_users)]

    send_mail(
        subject=f"{api_name} API Failure",
        message=f"A request to {api_name} has failed",
        from_email=None,
        recipient_list=admin_emails,
        fail_silently=False,
    )

@login_required
def trip_planner(request):
    if request.method == 'POST':
        destination = request.POST.get('destination')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            # Get coordinates using OpenWeatherMap Geocoding API
            api_key = os.environ['OPENWEATHER_API_KEY']
            geocoding_url = f"http://api.openweathermap.org/geo/1.0/direct?q={destination}&limit=1&appid={api_key}"
            
            response = requests.get(geocoding_url)
            response.raise_for_status()
            location_data = response.json()
            
            if not location_data:
                messages.error(request, f'Could not find coordinates for {destination}')
                return render(request, 'trips/trip_planner.html')
            
            # Extract coordinates from the first result
            latitude = location_data[0]['lat']
            longitude = location_data[0]['lon']
            
            trip = Trip.objects.create(
                user=request.user,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                latitude=latitude,
                longitude=longitude
            )
            messages.success(request, 'Trip created successfully!')
            return redirect('trips:my_trips')
        except requests.exceptions.RequestException as e:
            messages.error(request, f'Error getting location coordinates: {str(e)}')
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

    trip = get_object_or_404(Trip, id=id, user=request.user)
    
    # Ensure trip dates are properly formatted strings in the context
    formatted_start_date = trip.start_date.strftime('%A, %B %d, %Y').lstrip('0')
    formatted_end_date = trip.end_date.strftime('%A, %B %d, %Y').lstrip('0')

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
                'start_date': formatted_start_date,
                'end_date': formatted_end_date,
                'raw_start_date': trip.start_date,
                'raw_end_date': trip.end_date
            }
        }

    except requests.exceptions.RequestException as e:
        send_api_fail_email("OpenWeather")

        context = {
            'weather': {
                'days': [],
                'error': 'Failed to fetch weather data. Please try again later.'
            },
            'trip': {
                'destination': trip.destination,
                'start_date': formatted_start_date,
                'end_date': formatted_end_date,
                'raw_start_date': trip.start_date,
                'raw_end_date': trip.end_date
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
                'start_date': formatted_start_date,
                'end_date': formatted_end_date,
                'raw_start_date': trip.start_date,
                'raw_end_date': trip.end_date
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
            # Only update coordinates if destination has changed
            if destination != trip.destination:
                # Get coordinates using OpenWeatherMap Geocoding API
                api_key = os.environ['OPENWEATHER_API_KEY']
                geocoding_url = f"http://api.openweathermap.org/geo/1.0/direct?q={destination}&limit=1&appid={api_key}"
                
                response = requests.get(geocoding_url)
                response.raise_for_status()
                location_data = response.json()
                
                if not location_data:
                    messages.error(request, f'Could not find coordinates for {destination}')
                    return render(request, 'trips/edit_trip.html', {'trip': trip})
                
                # Extract coordinates from the first result
                trip.latitude = location_data[0]['lat']
                trip.longitude = location_data[0]['lon']
            
            trip.destination = destination
            trip.start_date = start_date
            trip.end_date = end_date
            trip.save()
            messages.success(request, 'Trip updated successfully!')
            return redirect('trips:my_trips')
        except requests.exceptions.RequestException as e:
            messages.error(request, f'Error getting location coordinates: {str(e)}')
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

@login_required
def view_packing_list(request, id):
    trip = get_object_or_404(Trip, id=id, user=request.user)
    items = PackingListItem.objects.filter(trip=trip)
    
    categories = {}
    for item in items:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)
    
    context = {
        'trip': trip,
        'categories': categories,
    }
    return render(request, 'trips/view_packing_list.html', context)

@login_required
@require_POST
def toggle_packed_status(request, trip_id, item_id):
    item = get_object_or_404(PackingListItem, id=item_id, trip_id=trip_id, trip__user=request.user)
    item.is_packed = not item.is_packed
    item.save()
    return JsonResponse({'status': 'success', 'is_packed': item.is_packed})

@login_required
@require_POST
def add_packing_item(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    name = request.POST.get('name')
    category = request.POST.get('category')
    quantity = request.POST.get('quantity', 1)
    must_have = request.POST.get('must_have') == 'on'  # Checkbox value
    
    if not name or not category:
        messages.error(request, 'Name and category are required.')
        return redirect('trips:view_packing_list', id=trip_id)
    
    PackingListItem.objects.create(
        trip=trip,
        name=name,
        category=category,
        quantity=quantity,
        must_have=must_have,
        is_auto_generated=False
    )
    messages.success(request, f'Added {name} to your packing list.')
    return redirect('trips:view_packing_list', id=trip_id)

@login_required
@require_POST
def delete_packing_item(request, trip_id, item_id):
    item = get_object_or_404(PackingListItem, id=item_id, trip_id=trip_id, trip__user=request.user)
    item.delete()
    messages.success(request, f'Removed {item.name} from your packing list.')
    return redirect('trips:view_packing_list', id=trip_id)

@login_required
@require_POST
def generate_packing_list(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    
    # Calculate trip duration
    duration = (trip.end_date - trip.start_date).days + 1
    
    # Get weather data for the trip
    api_key = os.environ['OPENWEATHER_API_KEY']
    weather_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={trip.latitude}&lon={trip.longitude}&units=imperial&appid={api_key}"
    
    try:
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        # Basic items everyone needs (with must-have items marked)
        basic_items = [
            ('Toiletries', [
                {'name': 'Toothbrush', 'must_have': True},
                {'name': 'Toothpaste', 'must_have': True},
                {'name': 'Deodorant', 'must_have': True},
                {'name': 'Shampoo', 'must_have': False},
                {'name': 'Soap', 'must_have': True}
            ]),
            ('Documents', [
                {'name': 'Passport', 'must_have': True},
                {'name': 'ID', 'must_have': True},
                {'name': 'Travel Insurance', 'must_have': True},
                {'name': 'Boarding Pass', 'must_have': True}
            ]),
            ('Electronics', [
                {'name': 'Phone Charger', 'must_have': True},
                {'name': 'Power Bank', 'must_have': False},
                {'name': 'Adapter', 'must_have': True}
            ]),
            ('Miscellaneous', [
                {'name': 'Wallet', 'must_have': True},
                {'name': 'Keys', 'must_have': True},
                {'name': 'Medications', 'must_have': True}
            ]),
        ]
        
        # Add basic items
        for category, items in basic_items:
            for item in items:
                item_name = item['name'] if isinstance(item, dict) else item
                must_have = item.get('must_have', False) if isinstance(item, dict) else False
                
                PackingListItem.objects.get_or_create(
                    trip=trip,
                    name=item_name,
                    category=category,
                    is_auto_generated=True,
                    defaults={'must_have': must_have}
                )
        
        # Add weather-specific items
        weather_items = []
        if any(forecast['main']['temp'] < 60 for forecast in weather_data['list']):
            weather_items.extend([
                ('Clothing', {'name': 'Warm Jacket', 'must_have': True}),
                ('Clothing', {'name': 'Sweater', 'must_have': False}),
                ('Accessories', {'name': 'Scarf', 'must_have': False}),
                ('Accessories', {'name': 'Gloves', 'must_have': False}),
            ])
        
        if any(forecast['main']['temp'] > 75 for forecast in weather_data['list']):
            weather_items.extend([
                ('Clothing', {'name': 'Sunglasses', 'must_have': True}),
                ('Toiletries', {'name': 'Sunscreen', 'must_have': True}),
                ('Clothing', {'name': 'Hat', 'must_have': False}),
                ('Clothing', {'name': 'Shorts', 'must_have': False}),
            ])
        
        if any(forecast.get('rain', {}).get('3h', 0) > 0 for forecast in weather_data['list']):
            weather_items.extend([
                ('Accessories', {'name': 'Umbrella', 'must_have': True}),
                ('Clothing', {'name': 'Rain Jacket', 'must_have': True}),
                ('Accessories', {'name': 'Waterproof Bag', 'must_have': False}),
            ])
        
        # Add weather-specific items
        for category, item in weather_items:
            item_name = item['name'] if isinstance(item, dict) else item
            must_have = item.get('must_have', False) if isinstance(item, dict) else False
            
            PackingListItem.objects.get_or_create(
                trip=trip,
                name=item_name,
                category=category,
                is_auto_generated=True,
                defaults={'must_have': must_have}
            )
        
        # Add clothing based on duration
        clothing_items = [
            ('Clothing', {'name': 'T-shirt', 'must_have': True}, duration),
            ('Clothing', {'name': 'Underwear', 'must_have': True}, duration),
            ('Clothing', {'name': 'Socks', 'must_have': True}, duration),
            ('Clothing', {'name': 'Pants', 'must_have': True}, (duration // 2) + 1),
        ]
        
        for category, item, count in clothing_items:
            item_name = item['name'] if isinstance(item, dict) else item
            must_have = item.get('must_have', False) if isinstance(item, dict) else False
            
            PackingListItem.objects.get_or_create(
                trip=trip,
                name=item_name,
                category=category,
                quantity=count,
                is_auto_generated=True,
                defaults={'must_have': must_have}
            )
        
        messages.success(request, 'Packing list generated successfully!')
        
    except requests.exceptions.RequestException as e:
        messages.error(request, 'Failed to generate packing list. Please try again later.')
    
    return redirect('trips:view_packing_list', id=trip_id)

def extract_items_from_outfit_description(outfit_description):
    """Helper function to extract and categorize outfit items from description text"""
    items = []
    lines = outfit_description.split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for bullet points or similar indicators
        if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
            item_text = line.lstrip('-•* ').strip()
            # Skip empty items or items that look like section headings
            if not item_text or item_text.endswith(':') or "cultural" in item_text.lower():
                continue
                
            # Simple category determination
            category = 'other'
            if any(word in item_text.lower() for word in ['shirt', 'top', 'tee', 't-shirt', 'blouse', 'sweater', 'polo']):
                category = 'top'
            elif any(word in item_text.lower() for word in ['pants', 'jeans', 'shorts', 'skirt', 'trouser']):
                category = 'bottom'
            elif any(word in item_text.lower() for word in ['jacket', 'coat', 'hoodie', 'cardigan', 'blazer']):
                category = 'outerwear'
            elif any(word in item_text.lower() for word in ['shoes', 'boots', 'sandals', 'sneakers', 'footwear']):
                category = 'footwear'
            elif any(word in item_text.lower() for word in ['hat', 'cap', 'sunglasses', 'scarf', 'gloves', 'umbrella']):
                category = 'accessory'
                
            items.append({
                'name': item_text,
                'category': category
            })
    
    return items

@login_required
def view_outfit_recommendations(request, id):
    trip = get_object_or_404(Trip, id=id, user=request.user)
    
    # Get or generate outfit recommendations
    recommendations = OutfitRecommendation.objects.filter(trip=trip).order_by('day')
    
    if not recommendations.exists():
        # Generate new recommendations using weather data and OpenAI
        api_key = os.environ['OPENWEATHER_API_KEY']
        weather_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={trip.latitude}&lon={trip.longitude}&units=imperial&appid={api_key}"
        
        try:
            weather_response = requests.get(weather_url)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            for forecast in weather_data['list']:
                forecast_time = datetime.fromtimestamp(forecast['dt'])
                forecast_date = forecast_time.date()
                
                if forecast_date < trip.start_date:
                    continue
                    
                if forecast_date > trip.end_date:
                    break
                
                # Only create one recommendation per day
                if not OutfitRecommendation.objects.filter(trip=trip, day=forecast_date).exists():
                    temp = forecast['main']['feels_like']
                    weather_desc = forecast['weather'][0]['main']
                    
                    # Determine season based on the month and hemisphere
                    month = forecast_date.month
                    # Rough approximation of seasons
                    northern_seasons = {
                        (12, 1, 2): 'Winter',
                        (3, 4, 5): 'Spring',
                        (6, 7, 8): 'Summer',
                        (9, 10, 11): 'Fall'
                    }
                    southern_seasons = {
                        (12, 1, 2): 'Summer',
                        (3, 4, 5): 'Fall',
                        (6, 7, 8): 'Winter',
                        (9, 10, 11): 'Spring'
                    }
                    
                    # Determine hemisphere based on latitude
                    is_northern = float(trip.latitude) >= 0
                    seasons = northern_seasons if is_northern else southern_seasons
                    
                    season = next((s for months, s in seasons.items() if month in months), 'Unknown')
                    
                    # Generate outfit recommendation and cultural notes using OpenAI
                    openai.api_key = os.environ.get('OPENAI_API_KEY')
                    
                    # First, get the outfit recommendations only
                    outfit_prompt = f"""For a day in {trip.destination} with temperature {temp}°F and {weather_desc} weather in {season} season, suggest a practical outfit.
                    Format your response as a simple list of clothing items ONLY, each on a separate line with a dash prefix.
                    Example:
                    - Item 1
                    - Item 2
                    - Item 3"""
                    
                    try:
                        # Get outfit recommendations
                        outfit_response = openai.completions.create(
                            model="gpt-3.5-turbo-instruct",
                            prompt=outfit_prompt,
                            max_tokens=150,
                            temperature=0.5
                        )
                        outfit_description = outfit_response.choices[0].text.strip()
                        
                        # If the outfit doesn't start with a dash, format it
                        if not outfit_description.strip().startswith('-'):
                            items = outfit_description.split('\n')
                            formatted_items = []
                            for item in items:
                                item = item.strip()
                                if item and not item.startswith('-'):
                                    formatted_items.append(f"- {item}")
                                elif item:
                                    formatted_items.append(item)
                            outfit_description = '\n'.join(formatted_items)
                        
                        # Now get cultural notes in a separate call
                        cultural_prompt = f"""Provide very brief cultural dress tips for visitors to {trip.destination} in 2-3 bullet points max.
                        Format as bullet points with dash prefix."""
                        
                        cultural_response = openai.completions.create(
                            model="gpt-3.5-turbo-instruct",
                            prompt=cultural_prompt,
                            max_tokens=100,
                            temperature=0.5
                        )
                        cultural_notes = cultural_response.choices[0].text.strip()
                    except Exception as e:
                        send_api_fail_email("OpenAI")
                        outfit_description = f"Default recommendation for {weather_desc} weather at {temp}°F"
                        cultural_notes = "Cultural information not available."
                    
                    recommendation = OutfitRecommendation.objects.create(
                        trip=trip,
                        day=forecast_date,
                        weather_condition=weather_desc,
                        temperature=temp,
                        outfit_description=outfit_description,
                        cultural_notes=cultural_notes
                    )
                    
                    # Extract and create individual outfit items
                    try:
                        # Use the helper function to extract items
                        outfit_items = extract_items_from_outfit_description(outfit_description)
                        
                        # Create the items in the database
                        for item in outfit_items:
                            OutfitItem.objects.create(
                                outfit=recommendation,
                                name=item['name'],
                                category=item['category']
                            )
                    except Exception as e:
                        # If parsing fails, don't worry - we still have the full outfit description
                        pass
            
            recommendations = OutfitRecommendation.objects.filter(trip=trip).order_by('day')
            messages.success(request, 'Outfit recommendations generated successfully!')
            
        except requests.exceptions.RequestException:
            send_api_fail_email("OpenWeather")
            messages.error(request, 'Failed to fetch weather data. Please try again later.')
        except Exception as e:
            messages.error(request, f'Error generating outfit recommendations: {str(e)}')
    
    # Get category choices from the model for the template
    category_choices = OutfitItem.CATEGORY_CHOICES
    
    context = {
        'trip': trip,
        'recommendations': recommendations,
        'category_choices': category_choices,
    }
    return render(request, 'trips/view_outfit_recommendations.html', context)

@login_required
@require_POST
def customize_outfit(request, trip_id, recommendation_id):
    recommendation = get_object_or_404(OutfitRecommendation, id=recommendation_id, trip_id=trip_id, trip__user=request.user)
    custom_outfit = request.POST.get('custom_outfit')
    activities = request.POST.get('activities')
    
    if custom_outfit:
        recommendation.outfit_description = custom_outfit
        recommendation.is_customized = True
        if activities:
            recommendation.activities = activities
        recommendation.save()
        messages.success(request, 'Outfit recommendation updated successfully!')
    else:
        messages.error(request, 'Please provide a custom outfit description.')
    
    # Detect if the request came from the detail page
    referer = request.META.get('HTTP_REFERER', '')
    if 'outfit-detail' in referer:
        return redirect('trips:view_outfit_detail', recommendation_id=recommendation_id)
    else:
        return redirect('trips:view_outfit_recommendations', id=trip_id)

def sync_outfit_items_to_packing_list(trip, outfit_recommendation):
    """
    Sync outfit items to the packing list, ensuring each item appears only once
    with the appropriate quantity.
    """
    # Get all outfit items for this recommendation
    outfit_items = outfit_recommendation.items.all()
    
    for outfit_item in outfit_items:
        # Try to find an existing packing list item with the same name
        existing_item = PackingListItem.objects.filter(
            trip=trip,
            name=outfit_item.name,
            category='Clothing'  # All outfit items go to Clothing category
        ).first()
        
        if existing_item:
            # If item exists, ensure quantity is at least 1
            if existing_item.quantity < 1:
                existing_item.quantity = 1
                existing_item.save()
        else:
            # Create new packing list item
            PackingListItem.objects.create(
                trip=trip,
                name=outfit_item.name,
                category='Clothing',
                quantity=1,
                is_auto_generated=True
            )

@login_required
@require_POST
def regenerate_outfit(request, trip_id, recommendation_id):
    recommendation = get_object_or_404(OutfitRecommendation, id=recommendation_id, trip_id=trip_id, trip__user=request.user)
    trip = recommendation.trip
    
    try:
        # Determine season based on the month and hemisphere
        month = recommendation.day.month
        # Rough approximation of seasons
        northern_seasons = {
            (12, 1, 2): 'Winter',
            (3, 4, 5): 'Spring',
            (6, 7, 8): 'Summer',
            (9, 10, 11): 'Fall'
        }
        southern_seasons = {
            (12, 1, 2): 'Summer',
            (3, 4, 5): 'Fall',
            (6, 7, 8): 'Winter',
            (9, 10, 11): 'Spring'
        }
        
        # Determine hemisphere based on latitude
        is_northern = float(trip.latitude) >= 0
        seasons = northern_seasons if is_northern else southern_seasons
        
        season = next((s for months, s in seasons.items() if month in months), 'Unknown')
        
        # Generate outfit recommendation and cultural notes using OpenAI
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        # Include activities in the prompt if they exist
        activities_text = ""
        if recommendation.activities:
            activities_text = f"Planned Activities: {recommendation.activities}"
        
        # First, get the outfit recommendations only
        outfit_prompt = f"""For a day in {trip.destination} with temperature {recommendation.temperature}°F and {recommendation.weather_condition} weather in {season} season, suggest a practical outfit.
        Format your response as a simple list of clothing items ONLY, each on a separate line with a dash prefix.
        Example:
        - Item 1
        - Item 2
        - Item 3
        {activities_text}"""
        
        try:
            # Get outfit recommendations
            outfit_response = openai.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=outfit_prompt,
                max_tokens=150,
                temperature=0.5
            )
            outfit_description = outfit_response.choices[0].text.strip()
            
            # If the outfit doesn't start with a dash, format it
            if not outfit_description.strip().startswith('-'):
                items = outfit_description.split('\n')
                formatted_items = []
                for item in items:
                    item = item.strip()
                    if item and not item.startswith('-'):
                        formatted_items.append(f"- {item}")
                    elif item:
                        formatted_items.append(item)
                outfit_description = '\n'.join(formatted_items)
            
            # Now get cultural notes in a separate call
            cultural_prompt = f"""Provide very brief cultural dress tips for visitors to {trip.destination} in 2-3 bullet points max.
            Format as bullet points with dash prefix."""
            
            cultural_response = openai.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=cultural_prompt,
                max_tokens=100,
                temperature=0.5
            )
            cultural_notes = cultural_response.choices[0].text.strip()
            
            # Update the recommendation
            recommendation.outfit_description = outfit_description
            recommendation.cultural_notes = cultural_notes
            recommendation.is_customized = False  # Reset customization flag
            recommendation.save()
            
            # Clear existing outfit items
            recommendation.items.all().delete()
            
            # Extract and create individual outfit items
            try:
                # Use the helper function to extract items
                outfit_items = extract_items_from_outfit_description(outfit_description)
                
                # Create the items in the database
                for item in outfit_items:
                    OutfitItem.objects.create(
                        outfit=recommendation,
                        name=item['name'],
                        category=item['category']
                    )
                
                # Sync with packing list
                sync_outfit_items_to_packing_list(trip, recommendation)
                    
            except Exception as e:
                # If parsing fails, don't worry - we still have the full outfit description
                pass
                
            messages.success(request, 'Outfit recommendation regenerated successfully!')
            
        except Exception as e:
            send_api_fail_email("OpenAI")
            messages.error(request, f'Error generating outfit recommendation: {str(e)}')
    
    except Exception as e:
        messages.error(request, f'Error processing request: {str(e)}')
    
    # Detect if the request came from the detail page
    referer = request.META.get('HTTP_REFERER', '')
    if 'outfit-detail' in referer:
        return redirect('trips:view_outfit_detail', recommendation_id=recommendation_id)
    else:
        return redirect('trips:view_outfit_recommendations', id=trip_id)

@login_required
def view_outfit_detail(request, recommendation_id):
    # Get the recommendation and verify that it belongs to the current user
    recommendation = get_object_or_404(OutfitRecommendation, id=recommendation_id, trip__user=request.user)
    trip = recommendation.trip
    
    # Get category choices from the model for the template
    category_choices = OutfitItem.CATEGORY_CHOICES
    
    context = {
        'trip': trip,
        'recommendation': recommendation,
        'category_choices': category_choices,
    }
    return render(request, 'trips/outfit_detail.html', context)

@login_required
def packing_list_stats(request, trip_id):
    """API endpoint to get packing list statistics for AJAX updates"""
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    items = PackingListItem.objects.filter(trip=trip)
    
    # Calculate overall stats
    total_items = items.count()
    packed_items = items.filter(is_packed=True).count()
    
    # Calculate per-category stats
    categories = {}
    for item in items:
        if item.category not in categories:
            categories[item.category] = {"total": 0, "packed": 0}
        
        categories[item.category]["total"] += 1
        if item.is_packed:
            categories[item.category]["packed"] += 1
    
    return JsonResponse({
        'total_items': total_items,
        'packed_items': packed_items,
        'categories': categories
    })

@login_required
@require_POST
def generate_smart_packing_list(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    
    try:
        # Get weather data
        api_key = os.environ['OPENWEATHER_API_KEY']
        weather_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={trip.latitude}&lon={trip.longitude}&units=imperial&appid={api_key}"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()
        
        # Prepare weather summary
        weather_summary = []
        for forecast in weather_data['list']:
            forecast_time = datetime.fromtimestamp(forecast['dt'])
            if trip.start_date <= forecast_time.date() <= trip.end_date:
                weather_summary.append({
                    'date': forecast_time.strftime('%Y-%m-%d'),
                    'temp': forecast['main']['feels_like'],
                    'weather': forecast['weather'][0]['main']
                })
        
        # Generate packing list using OpenAI
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        # More concise prompt to save tokens
        prompt = f"""Trip: {trip.destination}, Days: {(trip.end_date - trip.start_date).days + 1}, Weather: {weather_summary[0]['weather'] if weather_summary else 'Unknown'}, Temp: {weather_summary[0]['temp'] if weather_summary else 'Unknown'}°F.
        Create minimal packing list with categories: Clothing, Toiletries, Electronics, Miscellaneous.
        Format: JSON object with category names as keys, item arrays as values."""
        
        response = openai.completions.create(
            model="gpt-3.5-turbo-instruct",  # Cheaper model
            prompt=prompt,
            max_tokens=300,  # Limit response size
            temperature=0.5  # Lower creativity for more predictable responses
        )
        
        # Parse the response and create packing list items
        try:
            items_by_category = json.loads(response.choices[0].text)
            
            # Delete existing auto-generated items, except those from outfit recommendations
            PackingListItem.objects.filter(
                trip=trip,
                is_auto_generated=True,
                category__in=['Toiletries', 'Electronics', 'Miscellaneous']
            ).delete()
            
            # Create new items
            for category, items in items_by_category.items():
                # Skip clothing category as it will be handled by outfit recommendations
                if category.lower() == 'clothing':
                    continue
                    
                for item in items:
                    name = item
                    quantity = 1
                    
                    # If item is a dict with name and quantity
                    if isinstance(item, dict):
                        name = item.get('name', '')
                        quantity = item.get('quantity', 1)
                    
                    PackingListItem.objects.create(
                        trip=trip,
                        name=name,
                        category=category,
                        quantity=quantity,
                        is_auto_generated=True
                    )
            
            # Sync all outfit recommendations to the packing list
            outfit_recommendations = OutfitRecommendation.objects.filter(trip=trip)
            for recommendation in outfit_recommendations:
                sync_outfit_items_to_packing_list(trip, recommendation)
            
            messages.success(request, 'Smart packing list generated successfully!')
            
        except json.JSONDecodeError:
            messages.error(request, 'Error parsing AI response. Using fallback packing list.')
            # Call the original generate_packing_list function as fallback
            return generate_packing_list(request, trip_id)
            
    except Exception as e:
        send_api_fail_email("OpenAI")
        messages.error(request, f'Error generating smart packing list: {str(e)}')
    
    return redirect('trips:view_packing_list', id=trip_id)

@login_required
@require_POST
def add_outfit_item(request, trip_id, recommendation_id):
    recommendation = get_object_or_404(OutfitRecommendation, id=recommendation_id, trip_id=trip_id, trip__user=request.user)
    item_name = request.POST.get('item_name')
    category = request.POST.get('category')
    
    if item_name and category:
        # Create outfit item
        OutfitItem.objects.create(
            outfit=recommendation,
            name=item_name,
            category=category
        )
        recommendation.is_customized = True
        recommendation.save()
        
        # Sync with packing list
        sync_outfit_items_to_packing_list(recommendation.trip, recommendation)
        
        messages.success(request, f'Added {item_name} to your outfit!')
    else:
        messages.error(request, 'Please provide both item name and category.')
    
    # Detect if the request came from the detail page
    referer = request.META.get('HTTP_REFERER', '')
    if 'outfit-detail' in referer:
        return redirect('trips:view_outfit_detail', recommendation_id=recommendation_id)
    else:
        return redirect('trips:view_outfit_recommendations', id=trip_id)

@login_required
@require_POST
def remove_outfit_item(request, trip_id, recommendation_id, item_id):
    item = get_object_or_404(OutfitItem, id=item_id, outfit_id=recommendation_id, outfit__trip_id=trip_id, outfit__trip__user=request.user)
    item_name = item.name
    
    # Get the recommendation before deleting the item
    recommendation = item.outfit
    
    # Delete the item
    item.delete()
    
    # Mark the outfit as customized
    recommendation.is_customized = True
    recommendation.save()
    
    # Re-sync the outfit items with the packing list
    # This will ensure items are properly managed if they appear in multiple outfits
    sync_outfit_items_to_packing_list(recommendation.trip, recommendation)
    
    messages.success(request, f'Removed {item_name} from your outfit.')
    
    # Detect if the request came from the detail page
    referer = request.META.get('HTTP_REFERER', '')
    if 'outfit-detail' in referer:
        return redirect('trips:view_outfit_detail', recommendation_id=recommendation_id)
    else:
        return redirect('trips:view_outfit_recommendations', id=trip_id)

@login_required
@require_POST
def update_activities(request, trip_id, recommendation_id):
    recommendation = get_object_or_404(OutfitRecommendation, id=recommendation_id, trip_id=trip_id, trip__user=request.user)
    activities = request.POST.get('activities')
    
    recommendation.activities = activities
    recommendation.save()
    
    messages.success(request, 'Activities updated successfully!')
    
    # Detect if the request came from the detail page
    referer = request.META.get('HTTP_REFERER', '')
    if 'outfit-detail' in referer:
        return redirect('trips:view_outfit_detail', recommendation_id=recommendation_id)
    else:
        return redirect('trips:view_outfit_recommendations', id=trip_id)

@login_required
def all_outfits(request):
    user_trips = Trip.objects.filter(user=request.user)
    all_recommendations = OutfitRecommendation.objects.filter(trip__in=user_trips).order_by('-day')
    
    # If there are no recommendations at all, generate them for all trips
    if not all_recommendations.exists():
        for trip in user_trips:
            # Only generate for trips that don't have recommendations
            if not OutfitRecommendation.objects.filter(trip=trip).exists():
                try:
                    # Get weather data for the trip
                    api_key = os.environ['OPENWEATHER_API_KEY']
                    weather_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={trip.latitude}&lon={trip.longitude}&units=imperial&appid={api_key}"
                    
                    weather_response = requests.get(weather_url)
                    weather_response.raise_for_status()
                    weather_data = weather_response.json()
                    
                    for forecast in weather_data['list']:
                        forecast_time = datetime.fromtimestamp(forecast['dt'])
                        forecast_date = forecast_time.date()
                        
                        if forecast_date < trip.start_date:
                            continue
                            
                        if forecast_date > trip.end_date:
                            break
                        
                        # Only create one recommendation per day
                        if not OutfitRecommendation.objects.filter(trip=trip, day=forecast_date).exists():
                            temp = forecast['main']['feels_like']
                            weather_desc = forecast['weather'][0]['main']
                            
                            # Generate outfit recommendation using OpenAI
                            openai.api_key = os.environ.get('OPENAI_API_KEY')
                            
                            # Simple outfit request
                            outfit_prompt = f"""For a day in {trip.destination} with temperature {temp}°F and {weather_desc} weather, suggest a simple outfit.
                            Format your response as a list of clothing items, each on a separate line with a dash prefix."""
                            
                            try:
                                response = openai.completions.create(
                                    model="gpt-3.5-turbo-instruct",
                                    prompt=outfit_prompt,
                                    max_tokens=100,
                                    temperature=0.5
                                )
                                outfit_description = response.choices[0].text.strip()
                                
                                # Ensure proper formatting
                                if not outfit_description.strip().startswith('-'):
                                    items = outfit_description.split('\n')
                                    formatted_items = []
                                    for item in items:
                                        item = item.strip()
                                        if item and not item.startswith('-'):
                                            formatted_items.append(f"- {item}")
                                        elif item:
                                            formatted_items.append(item)
                                    outfit_description = '\n'.join(formatted_items)
                            except Exception as e:
                                send_api_fail_email("OpenAI")
                                outfit_description = f"Default recommendation for {weather_desc} weather at {temp}°F"
                            
                            recommendation = OutfitRecommendation.objects.create(
                                trip=trip,
                                day=forecast_date,
                                weather_condition=weather_desc,
                                temperature=temp,
                                outfit_description=outfit_description
                            )
                            
                            # Extract and create individual outfit items
                            try:
                                # Use the helper function to extract items
                                outfit_items = extract_items_from_outfit_description(outfit_description)
                                
                                # Create the items in the database
                                for item in outfit_items:
                                    OutfitItem.objects.create(
                                        outfit=recommendation,
                                        name=item['name'],
                                        category=item['category']
                                    )
                                
                                # Sync with packing list
                                sync_outfit_items_to_packing_list(trip, recommendation)
                            except Exception as e:
                                # If parsing fails, don't worry - we still have the full outfit description
                                pass
                    
                    messages.success(request, f'Outfit recommendations generated for {trip.destination}!')
                except Exception as e:
                    messages.error(request, f'Error generating recommendations for {trip.destination}: {str(e)}')
        
        # Refresh recommendations after generating
        all_recommendations = OutfitRecommendation.objects.filter(trip__in=user_trips).order_by('-day')
    
    context = {
        'recommendations': all_recommendations,
    }
    
    return render(request, 'trips/all_outfits.html', context)

@login_required
@require_POST
def generate_all_outfits(request):
    user_trips = Trip.objects.filter(user=request.user)
    
    if not user_trips.exists():
        messages.info(request, "You don't have any trips yet. Create a trip first!")
        return redirect('trips:trip_planner')
    
    generated_count = 0
    error_count = 0
    
    for trip in user_trips:
        try:
            # Get weather data for the trip
            api_key = os.environ['OPENWEATHER_API_KEY']
            weather_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={trip.latitude}&lon={trip.longitude}&units=imperial&appid={api_key}"
            
            weather_response = requests.get(weather_url)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            # Keep track of if we created any new recommendations for this trip
            trip_generated = False
            
            for forecast in weather_data['list']:
                forecast_time = datetime.fromtimestamp(forecast['dt'])
                forecast_date = forecast_time.date()
                
                if forecast_date < trip.start_date:
                    continue
                    
                if forecast_date > trip.end_date:
                    break
                
                # Only create one recommendation per day
                if not OutfitRecommendation.objects.filter(trip=trip, day=forecast_date).exists():
                    temp = forecast['main']['feels_like']
                    weather_desc = forecast['weather'][0]['main']
                    
                    # Generate outfit recommendation using OpenAI
                    openai.api_key = os.environ.get('OPENAI_API_KEY')
                    
                    # Simple outfit request
                    outfit_prompt = f"""For a day in {trip.destination} with temperature {temp}°F and {weather_desc} weather, suggest a simple outfit.
                    Format your response as a list of clothing items, each on a separate line with a dash prefix."""
                    
                    try:
                        response = openai.completions.create(
                            model="gpt-3.5-turbo-instruct",
                            prompt=outfit_prompt,
                            max_tokens=100,
                            temperature=0.5
                        )
                        outfit_description = response.choices[0].text.strip()
                        
                        # Ensure proper formatting
                        if not outfit_description.strip().startswith('-'):
                            items = outfit_description.split('\n')
                            formatted_items = []
                            for item in items:
                                item = item.strip()
                                if item and not item.startswith('-'):
                                    formatted_items.append(f"- {item}")
                                elif item:
                                    formatted_items.append(item)
                            outfit_description = '\n'.join(formatted_items)
                    except Exception as e:
                        send_api_fail_email("OpenAI")
                        outfit_description = f"Default recommendation for {weather_desc} weather at {temp}°F"
                    
                    recommendation = OutfitRecommendation.objects.create(
                        trip=trip,
                        day=forecast_date,
                        weather_condition=weather_desc,
                        temperature=temp,
                        outfit_description=outfit_description
                    )
                    
                    # Extract and create individual outfit items
                    try:
                        # Use the helper function to extract items
                        outfit_items = extract_items_from_outfit_description(outfit_description)
                        
                        # Create the items in the database
                        for item in outfit_items:
                            OutfitItem.objects.create(
                                outfit=recommendation,
                                name=item['name'],
                                category=item['category']
                            )
                        
                        # Sync with packing list
                        sync_outfit_items_to_packing_list(trip, recommendation)
                    except Exception as e:
                        # If parsing fails, don't worry - we still have the full outfit description
                        pass
                        
                    trip_generated = True
            
            if trip_generated:
                generated_count += 1
        except Exception:
            error_count += 1
    
    if generated_count > 0:
        messages.success(request, f'Generated outfit recommendations for {generated_count} trip(s)!')
    elif error_count == 0:
        messages.info(request, 'All trips already have outfit recommendations!')
    
    if error_count > 0:
        messages.error(request, f'Failed to generate recommendations for {error_count} trip(s)')
    
    return redirect('trips:all_outfits')

@login_required
@require_POST
def sync_outfit_to_packing_list(request, trip_id, recommendation_id):
    """
    Add all items from an outfit recommendation to the packing list
    """
    recommendation = get_object_or_404(OutfitRecommendation, id=recommendation_id, trip_id=trip_id, trip__user=request.user)
    
    try:
        # Extract items from the outfit description
        outfit_items = extract_items_from_outfit_description(recommendation.outfit_description)
        
        # Add each item to the packing list
        for item in outfit_items:
            # Check if item already exists
            existing_item = PackingListItem.objects.filter(
                trip_id=trip_id,
                name=item['name'],
                category='Clothing'
            ).first()
            
            if existing_item:
                # If item exists, ensure quantity is at least 1
                if existing_item.quantity < 1:
                    existing_item.quantity = 1
                    existing_item.save()
            else:
                # Create new packing list item
                PackingListItem.objects.create(
                    trip_id=trip_id,
                    name=item['name'],
                    category='Clothing',
                    quantity=1,
                    is_auto_generated=True
                )
        
        messages.success(request, 'Outfit items added to packing list successfully!')
    except Exception as e:
        messages.error(request, f'Error adding items to packing list: {str(e)}')
    
    # Redirect back to the outfit detail page
    return redirect('trips:view_outfit_detail', recommendation_id=recommendation_id)

@login_required
@require_POST
def update_item_quantity(request, trip_id, item_id):
    """
    Update the quantity of a packing list item
    """
    item = get_object_or_404(PackingListItem, id=item_id, trip_id=trip_id, trip__user=request.user)
    action = request.POST.get('action')
    
    try:
        if action == 'increase':
            item.quantity += 1
        elif action == 'decrease' and item.quantity > 1:
            item.quantity -= 1
        item.save()
        
        # Return JSON response for potential AJAX handling
        return JsonResponse({
            'status': 'success',
            'quantity': item.quantity,
            'can_decrease': item.quantity > 1
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
