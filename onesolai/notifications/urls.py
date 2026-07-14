from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_view, name='list'),
    path('<int:notif_id>/read/', views.mark_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('unread-count/', views.unread_count, name='unread_count'),
]
