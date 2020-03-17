from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm, StatusForm, ItemForm, CreateUserForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund
from django.contrib.auth.models import User
from .filters import ItemFilter, OrderFilter
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group

from .decorators import allowed_users, unauthenticated_user, admin_only

import random
import string

import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

@login_required(login_url='core:dashboard-login')
@admin_only
def Dashboard(request):
    orders = Order.objects.all() # Get all the orders
    total_orders = orders.filter(ordered=True).count() # Count total successful orders
   
    items = Item.objects.all() # Get all the items
    total_items = items.count() # Count total items

    users = User.objects.all() # Get all the users
    total_users = users.count() # Count total users

    # Get revenue by totalling all payment amounts
    payments = Payment.objects.all()
    revenue = 0
    for amounts in payments:
        revenue += amounts.amount

    # Filter all the orders which are successfully completed
    order_qs = Order.objects.filter(ordered=True)

    myFilter = OrderFilter(request.GET, queryset=order_qs)
    order_qs = myFilter.qs

    refund_granted = Order.objects.filter(ordered=True, refund_granted=True)
    for setorder in refund_granted:
        setorder.status = "Refund Granted"
        setorder.label = "primary"
        setorder.save()

    refund_requested = Order.objects.filter(ordered=True, refund_requested=True)
    for setorder in refund_requested:
        setorder.status = "Refund Requested"
        setorder.label = "danger"
        setorder.save()

    received = Order.objects.filter(ordered=True, received=True)
    for setorder in received:
        setorder.status = "Delivered"
        setorder.label = "complete"
        setorder.save()
    
    being_delivered = Order.objects.filter(ordered=True, being_delivered=True)
    for setorder in being_delivered:
        setorder.status = "Being Delivered"
        setorder.label = "secondary"
        setorder.save()

    # itemFilter = ItemFilter(request.GET, queryset=order_qs)
    # order_qs = itemFilter.qs
            
    context = {'total_orders':total_orders, 'total_items':total_items, 'revenue':revenue, 
                'total_users':total_users, 'orders':orders, 'order_qs':order_qs, 'myFilter':myFilter}

    return render(request, 'dashboard.html',context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid

class CheckoutView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm,
                'order': order,
                'DISPLAY_COUPON_FORM': True # Displays coupon form.
            }

            shipping_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'S',
                default = True
            )

            if shipping_address_qs.exists():
                context.update({'default_shipping_address': shipping_address_qs[0]})


            billing_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'B',
                default = True
            )

            if billing_address_qs.exists():
                context.update({'default_billing_address': billing_address_qs[0]})


            return render(self.request, 'checkout-page.html', context)

        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)

        try:
            # check if order is already exists and not yet completed.
            order = Order.objects.get(user=self.request.user, ordered=False)
            #print(self.request.POST) # printing the POST data to terminal
            if form.is_valid():

                # Get the cleaned data from the form.

                #------- If checkbox selected to use default shipping address --------
                use_default_shipping = form.cleaned_data.get('use_default_shipping')

                if use_default_shipping:
                    print("Using the default shipping address")
                    address_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'S',
                        default = True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()

                    else:
                        messages.info(self.request, "No default shipping address available")
                        return redirect('core:checkout')
                #----- Else user will enter new shipping address------------------------
                else:
                    print("User is entering a new shipping address")

                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')
                    
                    # functionality is above
                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        # Assign the data to Address model fields
                        shipping_address = Address(
                            user = self.request.user,
                            street_address = shipping_address1,
                            apartment_address = shipping_address2,
                            country = shipping_country,
                            zip = shipping_zip,
                            address_type = 'S'
                        )
                        shipping_address.save() # Save the assigned data

                        order.shipping_address = shipping_address
                        order.save()

                        #------- If checkbox selected to set default shipping address --------
                        set_default_shipping = form.cleaned_data.get('set_default_shipping')

                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                        #---------------------------------------------------------------------
                    else:
                        messages.info(self.request, "Please fill in the required shipping address fields")

#---------------------------- FOR BILLING ADDRESS ----------------------------------------

                #------- If checkbox selected to use default shipping address --------
                use_default_billing = form.cleaned_data.get('use_default_billing')
                #------- If checkbox selected to use same billing address as shipping address-
                same_billing_address = form.cleaned_data.get('same_billing_address')

                #------- If checkbox selected to use same billing address as shipping address-
                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                #------- elif checkbox selected to use default shipping address --------
                elif use_default_billing:
                    print("Using the default billing address")
                    address_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'B',
                        default = True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, "No default billing address available")
                        return redirect('core:checkout')
                #----- Else user will enter new billing address------------------------
                else:
                    print("User is entering a new billing address")

                    billing_address1 = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')
                    
                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        # Assign the data to Address model fields
                        shipping_address = Address(
                            user = self.request.user,
                            street_address = billing_address1,
                            apartment_address = billing_address2,
                            country = billing_country,
                            zip = billing_zip,
                            address_type = 'B'
                        )
                        billing_address.save() # Save the assigned data

                        order.billing_address = billing_address
                        order.save()

                        #------- If checkbox selected to set default shipping address --------
                        set_default_billing = form.cleaned_data.get('set_default_billing')

                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                        #---------------------------------------------------------------------
                    else:
                        messages.info(self.request, "Please fill in the required billing address fields")                


                payment_option = form.cleaned_data.get('payment_option')
               
                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'S':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    # Prints when data is invalid
                    messages.warning(self.request, "Invalid payment option selected")
                    return redirect('core:checkout')

        except ObjectDoesNotExist:
            # if there is no active order then shows message
            messages.warning(self.request, "You do not have active order")
            return redirect("core:order-summary")

        
class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False # Does not display coupon form.
            }
            return render(self.request, 'payment.html', context)
        else:
            messages.warning(self.request, "You have not added a billing address")
            return redirect("core:checkout")
    
    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken') # get from stripeTokenHandler in payment.html
        amount = int(order.get_total() * 100)
        

        try:
            charge = stripe.Charge.create(
                amount = amount,
                currency = "usd",
                source = "token",
            )

            # Create the payment
            payment = Payment()
            # Assign the values to Payment model fields
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            
            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            # Assign the payment to the order

            order.ordered = True # When order is completed
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()

            messages.success(self.request, "Your order was successful")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error',{})
            messages.warning(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate limit error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.warning(self.request, "Invalid parameters")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, "Not authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, "Network error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(self.request, "Something went wrong. You were not charged. Please try again.")
            return redirect("/")

        except Exception as e:
            # send an email to ourselves
            messages.warning(self.request, "A serious error occured. We have been notified")
            return redirect("/")


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home-page.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):

        try:
            # get the items which are not ordered yet from current user
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object':order
            }
            return render(self.request, 'order_summary.html', context)
            
        except ObjectDoesNotExist:
            # if there is no active order then shows message
            messages.warning(self.request, "You do not have active order")
            return redirect("/")
        
class ItemDetailView(DetailView):
    model = Item
    template_name = "product-page.html"

@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug) # get specific item with slug
    # If item is not in OrderItem model then add item else get the item
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
        )

    # filter Order model which is not ordered yet by the specific user
    order_qs = Order.objects.filter(user=request.user, ordered=False) 

    if order_qs.exists():
        order = order_qs[0] # grab the order from the order_qs

        # check if an item exists in Order model with slug
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1 # Increase quantity in OrderItem model if there is an item exists
            order_item.save() # Save OrderItem model
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item) # Add item to Order model if item does not exist in OrderItem.
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now() # get current date
        order = Order.objects.create(user=request.user, ordered_date=ordered_date) # Create Order model instance with specific user and ordered date
        order.items.add(order_item) # Then add order_item to that model instance
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug) # get specific item with slug

    # filter Order model which is not ordered yet by the specific user
    order_qs = Order.objects.filter(
        user=request.user, 
        ordered=False
    ) 

    if order_qs.exists():
        order = order_qs[0] # grab the order from the order_qs

        # check if an item exists in Order model with slug
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item) # Remove item if an item exists in Order model
            #------if item quantity is more than 1 and removed item from cart, Set item quantity to 1 in OrderItem
            if order_item.quantity > 1:
                order_item.quantity = 1
                order_item.save() # Save OrderItem model
            #-------------------------------------
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product",slug=slug)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect("core:product",slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug) # get specific item with slug

    # filter Order model which is not ordered yet by the specific user
    order_qs = Order.objects.filter(
        user=request.user, 
        ordered=False
    ) 

    if order_qs.exists():
        order = order_qs[0] # grab the order from the order_qs

        # check if an item exists in Order model with slug
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1 # Decrease quantity in OrderItem model if there is an item exists
                order_item.save() # Save OrderItem model
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product",slug=slug)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect("core:product",slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code) # Check if code exists
        return coupon # Return code

    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")

class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code') # Get the cleaned coupon code from form
                order = Order.objects.get(user=self.request.user, ordered=False)
                # Go to function and check if coupon exists? Yes. Add the coupon code to Order model field(coupon)
                order.coupon = get_coupon(self.request, code)
                order.save() # Save the order instance
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")

            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")

class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form':form
        }
        return render(self.request, 'refund_request.html', context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')

            # Edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # Store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")

@login_required(login_url='core:dashboard-login')
@admin_only
def UpdateStatusView(request, ref_code):
    order = Order.objects.get(ref_code=ref_code)
    form = StatusForm(instance=order)
    
    # Update specific order instances.
    if request.method == 'POST':
        form = StatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.info(request, "Updated order status successfully.")
            return redirect('core:dashboard')

    context = {
        'form':form,
        'order':order
    }
    return render(request, 'update_status.html', context)

#TODO: Decorator for permission
class ProductListView(LoginRequiredMixin, View):
    login_url = 'core:dashboard-login'
    def get(self, *args, **kwargs):
        items = Item.objects.all()
        context = {
            'items':items
        }
        return render(self.request, 'products_list.html', context)

@login_required(login_url='core:dashboard-login')
@admin_only
def UpdateItemView(request):
    item = Item.objects.get(quantity=3)
    form = ItemForm(instance=item)
    
    # Update specific item instances.
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.info(request, "Updated product details successfully.")
            return redirect('core:dashboard')

    context = {
        'form':form,
        'item':item
    }
    return render(request, 'update_item.html', context)

@unauthenticated_user
def DashboardRegister(request):
    # if request.user.is_authenticated:
    #     return redirect('core:dashboard')
    # else:
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')

            # For every user registration, add user to customer group
            group = Group.objects.get(name='customer')
            user.groups.add(group)

            messages.success(request,'Account was created for ' + username)
            return redirect('core:dashboard-login')
    context = {
        'form':form
    }
    return render(request, 'dashboard_register.html', context)


@unauthenticated_user
def DashboardLogin(request):
    # if request.user.is_authenticated:
    #     return redirect('core:dashboard')
    # else:
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        else:
            messages.info(request, 'Username OR password is incorrect')

    context = {}
    return render(request, 'dashboard_login.html', context)


def DashboardLogout(request):
    logout(request)
    return redirect('core:dashboard-login')


def DashboardUser(request):
    return render(request, 'dashboard_user.html')


