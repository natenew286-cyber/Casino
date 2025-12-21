import os

environment = os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.development')

if environment == 'config.settings.production':
    from .production import *
elif environment == 'config.settings.test':
    from .test import *
else:
    from .development import *