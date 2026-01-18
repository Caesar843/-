#!/usr/bin/env python
"""测试 URL 路由是否正确配置"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import get_resolver
from django.urls.exceptions import Resolver404

# 测试搜索 URL
test_paths = [
    '/api/search/search/',
    '/api/search/search/advanced/',
    '/api/search/quick-search/',
    '/api/search/autocomplete/',
    '/api/search/metrics/',
    '/api/i18n/translate/',
    '/api/i18n/convert-currency/',
    '/api/i18n/format-date/',
]

resolver = get_resolver()

for path in test_paths:
    try:
        match = resolver.resolve(path)
        print(f"[OK] {path} -> {match.func.__name__ if hasattr(match.func, '__name__') else match.view_name}")
    except Resolver404:
        print(f"[NOT FOUND] {path} -> 404 NOT FOUND")
