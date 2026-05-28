from django.contrib import admin

from .models import Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "quantity", "stock_status", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("name", "description")
    ordering = ("name",)

    @admin.display(description="Stock")
    def stock_status(self, obj):
        return "In stock" if obj.quantity > 0 else "Out of stock"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "line_total_display")
    can_delete = False

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        return obj.line_total


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer__username", "customer__email", "items__product_name")
    readonly_fields = ("customer", "status", "total", "created_at")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("customer").prefetch_related("items")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "unit_price", "quantity", "line_total_display")
    list_filter = ("order__created_at",)
    search_fields = ("product_name", "order__customer__username")
    readonly_fields = ("line_total_display",)

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        return obj.line_total
