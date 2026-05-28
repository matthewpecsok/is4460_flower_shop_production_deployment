from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="product_price_non_negative"),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="product_quantity_non_negative"),
        ]

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.quantity > 0


class Order(models.Model):
    class Status(models.TextChoices):
        SIMULATED_APPROVED = "SIMULATED_APPROVED", "Simulated approved"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SIMULATED_APPROVED,
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0), name="order_total_non_negative"),
        ]

    def __str__(self):
        return f"Order #{self.pk} for {self.customer}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    product_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="order_item_price_non_negative"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_item_quantity_positive"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
