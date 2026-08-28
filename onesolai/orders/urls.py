from django.urls import path
from .checkout_views import (
    checkout_view,
    payment_callback_view,
    flutterwave_callback_view,
    order_confirmation_view,
    crypto_checkout_view,
    submit_crypto_payment_view,
    manual_payment_page_view,
    submit_manual_payment_proof
)

app_name = 'orders'

urlpatterns = [
    path('checkout/', checkout_view, name='checkout'),
    path('crypto/<int:order_id>/', crypto_checkout_view, name='crypto_checkout'),
    path('crypto/<int:order_id>/submit/', submit_crypto_payment_view, name='submit_crypto_payment'),
    path('manual/<int:order_id>/', manual_payment_page_view, name='manual_payment'),
    path('manual/<int:order_id>/submit/', submit_manual_payment_proof, name='submit_manual_payment_proof'),
    path('callback/', payment_callback_view, name='payment_callback'),
    path('flutterwave/callback/', flutterwave_callback_view, name='flutterwave_callback'),
    path('confirmation/<int:order_id>/', order_confirmation_view, name='confirmation'),
]
