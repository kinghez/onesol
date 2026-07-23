from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/currencies/', views.api_currency_rates, name='api_currencies'),
    path('subscribe-newsletter/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
]
