from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/currencies/', views.api_currency_rates, name='api_currencies'),
]
