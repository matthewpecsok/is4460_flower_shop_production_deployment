from decimal import Decimal

from django.core.management.base import BaseCommand

from store.models import Product


class Command(BaseCommand):
    help = "Create sample flower products for classroom demonstrations without overwriting existing products."

    def handle(self, *args, **options):
        products = [
            {
                "name": "Classic Rose Bouquet",
                "description": "A dozen red roses arranged with greenery for celebrations and gifts.",
                "price": Decimal("49.99"),
                "quantity": 12,
            },
            {
                "name": "Spring Tulip Bundle",
                "description": "Bright mixed tulips wrapped simply for a cheerful seasonal arrangement.",
                "price": Decimal("29.50"),
                "quantity": 18,
            },
            {
                "name": "Sunflower Jar",
                "description": "Sunny sunflowers arranged in a reusable glass jar.",
                "price": Decimal("34.00"),
                "quantity": 8,
            },
            {
                "name": "Lavender Market Bunch",
                "description": "Fragrant lavender stems tied with twine for desks, counters, and gifts.",
                "price": Decimal("16.75"),
                "quantity": 20,
            },
        ]

        created_count = 0
        kept_count = 0
        for product_data in products:
            _, created = Product.objects.get_or_create(
                name=product_data["name"],
                defaults={
                    "description": product_data["description"],
                    "price": product_data["price"],
                    "quantity": product_data["quantity"],
                },
            )
            if created:
                created_count += 1
            else:
                kept_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo products ready. Created {created_count}; left {kept_count} existing products unchanged."
            )
        )
