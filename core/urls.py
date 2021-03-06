from django.urls import path
from .views import (
    HomeView,
    Dashboard,
    ItemDetailView, 
    OrderSummaryView,
    CheckoutView, 
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentView,
    AddCouponView,
    RequestRefundView,
    UpdateStatusView,
    ProductListView,
    UpdateItemView,
    DashboardRegister,
    DashboardLogin,
    DashboardLogout,
    DashboardUser
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name="home"),
    path('dashboard/', Dashboard, name="dashboard"),
    path('dashboard/update-status/<ref_code>/', UpdateStatusView, name='update-status'),
    path('dashboard/products-list/', ProductListView.as_view(), name='products-list'),
    path('dashboard/update-item/', UpdateItemView, name='update-item'),
    path('dashboard/register/', DashboardRegister, name='dashboard-register'),
    path('dashboard/login/', DashboardLogin, name='dashboard-login'),
    path('dashboard/logout/', DashboardLogout, name='dashboard-logout'),
    path('dashboard/user/', DashboardUser, name='dashboard-user'),
    path('checkout/', CheckoutView.as_view(), name="checkout"),
    path('order-summary/', OrderSummaryView.as_view(), name="order-summary"),
    path('product/<slug>/', ItemDetailView.as_view(), name="product"),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart, name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund')
]