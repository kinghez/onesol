from django.urls import path
from . import views

app_name = 'tools'

urlpatterns = [
    path('', views.tools_list, name='tools_list'),
    path('api/', views.api_tools_json, name='api_tools'),
    path('<slug:slug>/', views.tool_detail, name='tool_detail'),
]
