from django.urls import path
from . import api_v1_views as views

app_name = 'api_v1'

urlpatterns = [
    # Catalog / Tools
    path('tools/', views.v1_list_tools, name='list_tools'),
    path('tools/<int:tool_id>/', views.v1_tool_detail, name='tool_detail'),

    # Profile & Account
    path('me/', views.v1_user_profile, name='user_profile'),
    path('me/orders/', views.v1_user_orders, name='user_orders'),
    path('me/orders/<int:order_id>/', views.v1_order_detail, name='order_detail'),

    # Wishlist
    path('me/wishlist/', views.v1_user_wishlist, name='user_wishlist'),
    path('me/wishlist/<int:wishlist_id>/', views.v1_remove_wishlist, name='remove_wishlist'),

    # Purchasing & Wallet
    path('orders/buy/', views.v1_buy_tool, name='buy_tool'),
    path('wallet/topup/', views.v1_wallet_topup, name='wallet_topup'),

    # Notifications
    path('me/notifications/', views.v1_user_notifications, name='user_notifications'),
    path('me/notifications/mark-read/', views.v1_mark_notifications_read, name='mark_notifications_read'),
]
