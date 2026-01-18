#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.i18n_manager import I18nManager

manager_de = I18nManager('de')
result = manager_de.format_number(1234.56)
print(f'German: {result}')
print(f'Has dot (.): {"." in result}')
print(f'Has comma (,): {"," in result}')

manager_en = I18nManager('en')
result_en = manager_en.format_number(1234567.89)
print(f'\nEnglish (1234567.89): {result_en}')
print(f'Has comma: {"," in result_en}')
