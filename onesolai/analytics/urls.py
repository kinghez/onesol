from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.admin_analytics_dashboard, name='dashboard'),
    path('vendor-wallets/', views.vendor_wallets_view, name='vendor_wallets'),
    path('platform-wallet/', views.platform_wallet_view, name='platform_wallet'),
    path('reload-balances/', views.reload_vendor_balances, name='reload_balances'),
]
