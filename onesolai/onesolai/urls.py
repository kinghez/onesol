from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home
    path('', include('core.home_urls')),

    # Auth
    path('auth/', include('accounts.urls')),

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
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
