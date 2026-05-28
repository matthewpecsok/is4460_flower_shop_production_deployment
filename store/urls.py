from django.urls import path

from . import views


app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("catalog/", views.product_list, name="catalog"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("register/", views.register, name="register"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/confirmation/", views.order_confirmation, name="order_confirmation"),
]
