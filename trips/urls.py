from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('planner/', views.trip_planner, name='trip_planner'),
] 