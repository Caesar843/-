#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from apps.core.i18n_manager import I18nManager

manager = I18nManager(language='en')
result = manager.format_currency(Decimal('1234.56'), 'USD')
print(f'Result: {result}')
print(f'Has $: {"$" in result}')
print(f'Has 1234.56: {"1234.56" in result}')
print(f'Has 1,234.56: {"1,234.56" in result}')
