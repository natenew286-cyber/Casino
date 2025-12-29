import os

environment = os.getenv('DJANGO_SETTINGS_MODULE', 'config.base')

if environment == 'config.production':
    from .production import *
elif environment == 'config.test':
    from .test import *
elif environment == 'config.development':
    from .development import *
else:
    # Default to base settings
    from .base import *