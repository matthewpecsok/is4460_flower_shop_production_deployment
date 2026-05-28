from decimal import Decimal

from .models import Product


CART_SESSION_KEY = "cart"


def get_cart(session):
    raw_cart = session.get(CART_SESSION_KEY, {})
    cart = {}
    for product_id, quantity in raw_cart.items():
        try:
            parsed_id = str(int(product_id))
            parsed_quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if parsed_quantity > 0:
            cart[parsed_id] = parsed_quantity
    return cart


def save_cart(session, cart):
    cleaned_cart = {}
    for product_id, quantity in cart.items():
        try:
            parsed_id = str(int(product_id))
            parsed_quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if parsed_quantity > 0:
            cleaned_cart[parsed_id] = parsed_quantity
    session[CART_SESSION_KEY] = cleaned_cart
    session.modified = True


def clear_cart(session):
    session[CART_SESSION_KEY] = {}
    session.modified = True


def cart_quantity(session):
    return sum(get_cart(session).values())


def build_cart_lines(session, normalize=False):
    cart = get_cart(session)
    product_ids = [int(product_id) for product_id in cart]
    products = Product.objects.filter(pk__in=product_ids).in_bulk()
    lines = []
    total = Decimal("0.00")
    changed = False
    normalized_cart = {}

    for product_id, quantity in cart.items():
        product = products.get(int(product_id))
        if product is None or product.quantity < 1:
            changed = True
            continue

        safe_quantity = min(quantity, product.quantity)
        if safe_quantity != quantity:
            changed = True

        line_total = product.price * safe_quantity
        total += line_total
        normalized_cart[product_id] = safe_quantity
        lines.append(
            {
                "product": product,
                "quantity": safe_quantity,
                "line_total": line_total,
            }
        )

    if normalize and changed:
        save_cart(session, normalized_cart)

    return lines, total
