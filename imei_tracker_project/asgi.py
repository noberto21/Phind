"""
ASGI config for imei_tracker_project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imei_tracker_project.settings')

application = get_asgi_application()
