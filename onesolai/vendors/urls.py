from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('webhook/shopbot/', views.shopbot_webhook, name='shopbot_webhook'),
]
