import django_filters

from .models import *

class OrderFilter(django_filters.FilterSet):
    class Meta:
        model = Order
        fields = {
            'user',
            'items'
        }

class ItemFilter(django_filters.FilterSet):
    class Meta:
        model = Item
        fields = {
            'title'
        }