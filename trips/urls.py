from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('planner/', views.trip_planner, name='trip_planner'),
    path('<int:id>/weather/', views.view_weather, name='view_weather'),
] 