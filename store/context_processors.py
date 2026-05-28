from .cart import cart_quantity


def cart_summary(request):
    return {"cart_item_count": cart_quantity(request.session)}
