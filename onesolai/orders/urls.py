from django.urls import path
from .checkout_views import checkout_view, payment_callback_view, flutterwave_callback_view, order_confirmation_view

app_name = 'orders'

urlpatterns = [
    path('checkout/', checkout_view, name='checkout'),
    path('callback/', payment_callback_view, name='payment_callback'),
    path('flutterwave/callback/', flutterwave_callback_view, name='flutterwave_callback'),
    path('confirmation/<int:order_id>/', order_confirmation_view, name='confirmation'),
]
