from django.urls import path
from .views import item_list, product, checkout

app_name = 'core'

urlpatterns = [
    path('', item_list, name="item-list"),
    path('product/', product, name="product"),
    path('checkout/', checkout, name="checkout")
]