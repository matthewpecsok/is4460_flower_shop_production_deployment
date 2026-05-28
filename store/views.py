from decimal import Decimal
import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import build_cart_lines, clear_cart, get_cart, save_cart
from .forms import CustomerRegistrationForm
from .models import Order, OrderItem, Product


logger = logging.getLogger(__name__)


def parse_quantity(raw_value):
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def home(request):
    featured_products = Product.objects.filter(quantity__gt=0)[:3]
    return render(request, "store/home.html", {"featured_products": featured_products})


def product_list(request):
    products = Product.objects.all()
    return render(request, "store/product_list.html", {"products": products})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "store/product_detail.html", {"product": product})


def register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. You are now signed in.")
            return redirect("store:catalog")
        logger.warning("Customer registration validation failed.")
    else:
        form = CustomerRegistrationForm()
    return render(request, "store/register.html", {"form": form})


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    quantity = parse_quantity(request.POST.get("quantity", "1"))

    if quantity is None or quantity < 1:
        messages.error(request, "Enter a quantity of at least 1.")
        return redirect("store:product_detail", pk=product.pk)

    if product.quantity < 1:
        messages.error(request, f"{product.name} is currently out of stock.")
        return redirect("store:product_detail", pk=product.pk)

    cart = get_cart(request.session)
    current_quantity = cart.get(str(product.pk), 0)
    requested_total = current_quantity + quantity
    safe_total = min(requested_total, product.quantity)

    cart[str(product.pk)] = safe_total
    save_cart(request.session, cart)

    if safe_total < requested_total:
        messages.warning(request, f"Cart quantity was limited to the {product.quantity} currently available.")
    else:
        messages.success(request, f"Added {product.name} to your cart.")
    return redirect("store:cart_detail")


def cart_detail(request):
    lines, total = build_cart_lines(request.session, normalize=True)
    return render(request, "store/cart_detail.html", {"cart_lines": lines, "cart_total": total})


@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    quantity = parse_quantity(request.POST.get("quantity"))

    if quantity is None or quantity < 1:
        messages.error(request, "Cart quantities must be at least 1.")
        return redirect("store:cart_detail")

    cart = get_cart(request.session)
    if product.quantity < 1:
        cart.pop(str(product.pk), None)
        save_cart(request.session, cart)
        messages.warning(request, f"{product.name} is now out of stock and was removed from your cart.")
        return redirect("store:cart_detail")

    safe_quantity = min(quantity, product.quantity)
    cart[str(product.pk)] = safe_quantity
    save_cart(request.session, cart)

    if safe_quantity < quantity:
        messages.warning(request, f"Quantity was limited to the {product.quantity} currently available.")
    else:
        messages.success(request, "Cart updated.")
    return redirect("store:cart_detail")


@require_POST
def remove_from_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = get_cart(request.session)
    cart.pop(str(product.pk), None)
    save_cart(request.session, cart)
    messages.success(request, f"Removed {product.name} from your cart.")
    return redirect("store:cart_detail")


@login_required
@require_POST
def checkout(request):
    cart = get_cart(request.session)
    if not cart:
        messages.info(request, "Your cart is empty.")
        return redirect("store:catalog")

    try:
        with transaction.atomic():
            product_ids = [int(product_id) for product_id in cart]
            products = Product.objects.select_for_update().filter(pk__in=product_ids).in_bulk()
            stock_errors = []

            for product_id, quantity in cart.items():
                product = products.get(int(product_id))
                if product is None:
                    stock_errors.append("A product in your cart is no longer available.")
                elif quantity < 1:
                    stock_errors.append(f"{product.name} has an invalid cart quantity.")
                elif quantity > product.quantity:
                    stock_errors.append(
                        f"{product.name} has only {product.quantity} available, but your cart has {quantity}."
                    )

            if stock_errors:
                logger.warning(
                    "Checkout failed due to insufficient inventory user_id=%s username=%s errors=%s",
                    request.user.id,
                    request.user.username,
                    stock_errors,
                )
                for error in stock_errors:
                    messages.error(request, error)
                return redirect("store:cart_detail")

            order = Order.objects.create(customer=request.user)
            total = Decimal("0.00")

            for product_id, quantity in cart.items():
                product = products[int(product_id)]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=quantity,
                )
                total += product.price * quantity
                product.quantity -= quantity
                product.save(update_fields=["quantity", "updated_at"])

            order.total = total
            order.save(update_fields=["total"])

        clear_cart(request.session)
        logger.info(
            "Created simulated order order_id=%s user_id=%s username=%s total=%s",
            order.id,
            request.user.id,
            request.user.username,
            order.total,
        )
        messages.success(request, "Simulated purchase approved. Your order has been saved.")
        return redirect("store:order_confirmation", order_id=order.id)
    except Exception:
        logger.exception("Unexpected checkout error user_id=%s username=%s", request.user.id, request.user.username)
        messages.error(request, "Something went wrong while saving your order. Please try again.")
        return redirect("store:cart_detail")


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(
        Order.objects.filter(customer=request.user).prefetch_related("items"),
        pk=order_id,
    )
    return render(request, "store/order_confirmation.html", {"order": order})


@login_required
def order_list(request):
    orders = Order.objects.filter(customer=request.user).prefetch_related("items")
    return render(request, "store/order_list.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.filter(customer=request.user).prefetch_related("items"),
        pk=order_id,
    )
    return render(request, "store/order_detail.html", {"order": order})
