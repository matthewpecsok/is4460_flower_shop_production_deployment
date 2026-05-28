"""ASGI config for the flower shop project."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flower_shop.settings")

application = get_asgi_application()
