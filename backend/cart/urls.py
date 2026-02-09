from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_cart, name='cart-detail'),               
    path('add/', views.add_to_cart, name='cart-add'),          
    path('update/<int:item_id>/', views.update_cart_item, name='cart-update'), 
    path('remove/<int:item_id>/', views.remove_cart_item, name='cart-remove'),  
    path('clear/', views.clear_cart, name='cart-clear'),        
]
