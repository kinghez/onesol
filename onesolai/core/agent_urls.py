from django.urls import path
from . import agent_api_views as views

app_name = 'agent_api'

urlpatterns = [
    # Catalog & Purchasing Tools
    path('tools/', views.agent_check_tools, name='check_tools'),
    path('buy-tool/', views.agent_buy_tool, name='buy_tool'),
    path('add-to-wishlist/', views.agent_add_to_wishlist, name='add_to_wishlist'),

    # User Profile, Wallet, Referrals, Withdrawals & Order Status Tools
    path('user-profile/', views.agent_user_profile, name='user_profile'),
    path('user-wallet/', views.agent_user_wallet, name='user_wallet'),
    path('user-referrals/', views.agent_user_referrals, name='user_referrals'),
    path('user-withdrawals/', views.agent_user_withdrawals, name='user_withdrawals'),
    path('order-status/', views.agent_order_status, name='order_status'),
]
