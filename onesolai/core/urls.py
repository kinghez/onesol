from django.urls import path
from . import views, dashboard_views, profile_views, wallet_views
from .referral_views import referrals_view, withdrawal_request_view
from .refund_views import request_refund_view

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.dashboard_home, name='home'),
    path('profile/', profile_views.profile_settings_view, name='profile'),
    path('security/', profile_views.security_view, name='security'),
    path('support/', profile_views.support_view, name='support'),
    path('wallet/', wallet_views.wallet_dashboard_view, name='wallet'),
    path('wallet/topup/', wallet_views.wallet_topup_initialize, name='wallet_topup'),
    path('wallet/topup/callback/', wallet_views.wallet_topup_callback, name='wallet_topup_callback'),
    path('subscriptions/', dashboard_views.subscriptions, name='subscriptions'),
    path('orders/', dashboard_views.order_history_view, name='order_history'),
    path('orders/<int:order_id>/', dashboard_views.order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/refund/', request_refund_view, name='request_refund'),
    path('referrals/', referrals_view, name='referrals'),
    path('referrals/withdraw/', withdrawal_request_view, name='withdraw'),
    path('wishlist/', dashboard_views.wishlist_view, name='wishlist'),
]
