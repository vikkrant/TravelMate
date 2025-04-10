from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('planner/', views.trip_planner, name='trip_planner'),
    path('my-trips/', views.my_trips, name='my_trips'),
    path('weather/<int:id>/', views.view_weather, name='view_weather'),
    path('edit/<int:id>/', views.edit_trip, name='edit_trip'),
    path('delete/<int:id>/', views.delete_trip, name='delete_trip'),
] 