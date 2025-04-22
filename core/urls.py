from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('test-dark-mode/', views.test_dark_mode, name='test_dark_mode'),
    path('test/', views.test, name='test'),
] 