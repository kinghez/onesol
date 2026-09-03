from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('', views.home, name='home'),
    path('about-us/', views.about_us, name='about_us'),
    path('api/currencies/', views.api_currency_rates, name='api_currencies'),
    path('subscribe-newsletter/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('features/', views.features_page, name='features'),
    path('contact/', views.contact_us, name='contact_us'),
    path('refer-and-earn/', views.refer_and_earn, name='refer_and_earn'),
    path('developer/docs/', views.api_docs_view, name='api_docs'),
]
