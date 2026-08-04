from django.urls import path
from . import agent_api_views as views

app_name = 'agent_api'

urlpatterns = [
    path('tools/', views.agent_check_tools, name='check_tools'),
    path('buy-tool/', views.agent_buy_tool, name='buy_tool'),
    path('add-to-wishlist/', views.agent_add_to_wishlist, name='add_to_wishlist'),
]
