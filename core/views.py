from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.shortcuts import redirect
from django.utils import timezone
from .models import Item, OrderItem, Order

def checkout(request):
    return render(request, 'checkout-page.html')

class HomeView(ListView):
    model = Item
    template_name = "home-page.html"

class ItemDetailView(DetailView):
    model = Item
    template_name = "product-page.html"

def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug) # get specific item with slug
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
        )
    order_qs = Order.objects.filter(user=request.user, ordered=False) # filter order which is not completed by the specific user

    if order_qs.exists():
        order = order_qs[0] # grab the order from the order_qs
        # check if the order item in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
        else:
            order.items.add(order_item)
    else:
        ordered_date = timezone.now() # get current date
        order = Order.objects.create(user=request.user, ordered_date=ordered_date) # Create Order model instance with specific user and ordered date
        order.items.add(order_item) # Then add order_item to that model instance
    return redirect("core:product",slug=slug)


"""
Function based view for homepage

def home(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, 'home-page.html', context)
"""

