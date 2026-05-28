from decimal import Decimal
import logging

import pytest
from django.urls import reverse

from .cart import CART_SESSION_KEY
from .models import Order, OrderItem, Product


pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    return Product.objects.create(
        name="Test Roses",
        description="A bouquet for tests.",
        price=Decimal("19.99"),
        quantity=5,
    )


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(username="customer", password="password12345")


def put_cart(client, product, quantity):
    session = client.session
    session[CART_SESSION_KEY] = {str(product.pk): quantity}
    session.save()


def response_text(response):
    return response.content.decode(response.charset or "utf-8")


def allow_caplog_to_capture_store_logs(monkeypatch):
    monkeypatch.setattr(logging.getLogger("store"), "propagate", True)
    monkeypatch.setattr(logging.getLogger("store.views"), "propagate", True)


def test_catalog_and_detail_pages_load(client, product):
    catalog_response = client.get(reverse("store:catalog"))
    detail_response = client.get(reverse("store:product_detail", args=[product.pk]))

    assert catalog_response.status_code == 200
    assert product.name in response_text(catalog_response)
    assert detail_response.status_code == 200
    assert "Quantity available" in response_text(detail_response)


def test_registration_creates_non_staff_customer(client, django_user_model):
    response = client.post(
        reverse("store:register"),
        {
            "username": "newcustomer",
            "email": "new@example.com",
            "password1": "strong-test-password-123",
            "password2": "strong-test-password-123",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("store:catalog")
    user = django_user_model.objects.get(username="newcustomer")
    assert user.is_staff is False
    assert user.is_superuser is False


def test_purchase_and_orders_require_login(client, product):
    put_cart(client, product, 1)

    checkout_response = client.post(reverse("store:checkout"))
    order_list_response = client.get(reverse("store:order_list"))

    assert checkout_response.status_code == 302
    assert reverse("login") in checkout_response["Location"]
    assert order_list_response.status_code == 302
    assert reverse("login") in order_list_response["Location"]


def test_add_product_to_cart(client, product):
    response = client.post(reverse("store:add_to_cart", args=[product.pk]), {"quantity": "2"})

    assert response.status_code == 302
    assert response["Location"] == reverse("store:cart_detail")
    assert client.session[CART_SESSION_KEY][str(product.pk)] == 2


def test_update_and_remove_cart_items(client, product):
    put_cart(client, product, 1)

    update_response = client.post(
        reverse("store:update_cart", args=[product.pk]),
        {"quantity": "3"},
    )
    assert update_response.status_code == 302
    assert update_response["Location"] == reverse("store:cart_detail")
    assert client.session[CART_SESSION_KEY][str(product.pk)] == 3

    remove_response = client.post(reverse("store:remove_from_cart", args=[product.pk]))
    assert remove_response.status_code == 302
    assert remove_response["Location"] == reverse("store:cart_detail")
    assert str(product.pk) not in client.session[CART_SESSION_KEY]


def test_cart_prevents_quantity_greater_than_inventory(client, product):
    response = client.post(reverse("store:add_to_cart", args=[product.pk]), {"quantity": "99"})

    assert response.status_code == 302
    assert response["Location"] == reverse("store:cart_detail")
    assert client.session[CART_SESSION_KEY][str(product.pk)] == product.quantity


def test_successful_simulated_purchase_creates_order_and_updates_inventory(
    client,
    product,
    customer,
    caplog,
    monkeypatch,
):
    client.login(username="customer", password="password12345")
    put_cart(client, product, 2)
    allow_caplog_to_capture_store_logs(monkeypatch)

    with caplog.at_level(logging.INFO, logger="store.views"):
        response = client.post(reverse("store:checkout"))

    order = Order.objects.get(customer=customer)
    product.refresh_from_db()

    assert response.status_code == 302
    assert response["Location"] == reverse("store:order_confirmation", args=[order.pk])
    assert order.total == Decimal("39.98")
    assert order.items.count() == 1
    assert order.items.first().product_name == "Test Roses"
    assert product.quantity == 3
    assert client.session[CART_SESSION_KEY] == {}
    assert "Created simulated order" in caplog.text


def test_checkout_failure_when_stock_is_insufficient_is_atomic(
    client,
    product,
    customer,
    caplog,
    monkeypatch,
):
    client.login(username="customer", password="password12345")
    put_cart(client, product, 4)
    product.quantity = 2
    product.save()
    allow_caplog_to_capture_store_logs(monkeypatch)

    with caplog.at_level(logging.WARNING, logger="store.views"):
        response = client.post(reverse("store:checkout"))

    product.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == reverse("store:cart_detail")
    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0
    assert product.quantity == 2
    assert client.session[CART_SESSION_KEY][str(product.pk)] == 4
    assert "Checkout failed due to insufficient inventory" in caplog.text


def test_customers_can_view_their_own_orders(client, product, customer):
    order = Order.objects.create(customer=customer, total=Decimal("19.99"))
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
    )
    client.login(username="customer", password="password12345")

    list_response = client.get(reverse("store:order_list"))
    detail_response = client.get(reverse("store:order_detail", args=[order.pk]))

    assert f"Order #{order.pk}" in response_text(list_response)
    assert product.name in response_text(detail_response)


def test_customers_cannot_view_other_customers_orders(client, django_user_model, customer):
    other_user = django_user_model.objects.create_user(username="other", password="password12345")
    order = Order.objects.create(customer=other_user, total=Decimal("19.99"))
    client.login(username="customer", password="password12345")

    response = client.get(reverse("store:order_detail", args=[order.pk]))

    assert response.status_code == 404


def test_admin_product_management_requires_staff(client, product, customer, django_user_model):
    admin_url = reverse("admin:store_product_changelist")

    anonymous_response = client.get(admin_url)
    assert anonymous_response.status_code == 302

    client.login(username="customer", password="password12345")
    non_staff_response = client.get(admin_url)
    assert non_staff_response.status_code in [302, 403]

    staff_user = django_user_model.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password12345",
    )
    client.force_login(staff_user)
    staff_response = client.get(admin_url)

    assert staff_response.status_code == 200
    assert product.name in response_text(staff_response)
