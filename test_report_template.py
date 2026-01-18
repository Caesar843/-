"""
报告模板测试脚本（用于诊断目的，不是 Django 单元测试）
此脚本不应被 manage.py test 自动发现和运行
"""

from django.template import Template, Context
from django.conf import settings

# 配置Django环境（仅当未配置时）
if not settings.configured:
    settings.configure(
        DEBUG=True,
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': ['templates'],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                    ],
                },
            },
        ],
    )

import django
if not settings.configured:
    django.setup()

# 读取模板文件
with open('templates/reports/report_list.html', 'r', encoding='utf-8') as f:
    template_content = f.read()

# 渲染模板
context = Context({
    'report_type': 'shop_operation',
    'start_date': '2026-01-01',
    'end_date': '2026-01-15',
    'shops': [],
    'report_data': {},
    'now': '2026-01-15 12:00:00',
})

template = Template(template_content)
try:
    rendered = template.render(context)
    print('[OK] Template rendered successfully. No TemplateSyntaxError.')
    print('The fix for the "Invalid filter: \'sum\'" error has been applied.')
except Exception as e:
    print(f'[ERROR] Template rendering failed with error: {e}')
    print('The fix for the "Invalid filter: \'sum\'" error has NOT been applied correctly.')
