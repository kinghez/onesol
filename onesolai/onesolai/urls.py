from django.contrib import admin
from django.urls import path, include, re_path
from accounts import views as accounts_views
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Google Search Console HTML Verification
    path('google595a3ac64208eb4d.html', core_views.google_verification, name='google_verification'),

    # Home
    path('', include('core.home_urls')),

    # Auth
    path('auth/', include('accounts.urls')),
    
    # Auth Direct Aliases
    path('auth/google/login/', accounts_views.google_login_view, name='google_login'),
    path('auth/google/callback/', accounts_views.google_callback_view, name='google_callback'),

    # Tools / Products
    path('tools/', include('products.urls')),

    # Orders & Payments
    path('orders/', include('orders.urls')),

    # Dashboard
    path('dashboard/', include('core.urls')),

    # Notifications
    path('notifications/', include('notifications.urls')),

    # Vendors (Webhooks etc)
    path('vendors/', include('vendors.urls')),

    # Custom Admin Analytics
    path('dashboard/admin-analytics/', include('analytics.urls')),

    # AI Agent Integration API
    path('api/agent/', include('core.agent_urls')),

    # Public Developer API (v1)
    path('api/v1/', include('core.api_v1_urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
