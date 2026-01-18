"""
国际化系统单元测试

包括配置、管理器、API、集成和性能测试。
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from datetime import datetime
from decimal import Decimal
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import pytz

from apps.core.i18n_manager import I18nManager, I18nFactory, get_i18n_manager
from apps.core.i18n_config import (
    DEFAULT_LANGUAGE,
    DEFAULT_CURRENCY,
    DEFAULT_TIMEZONE,
    SUPPORTED_LANGUAGES,
    SUPPORTED_CURRENCIES,
    SUPPORTED_TIMEZONES,
    get_language_config,
    get_currency_info,
    get_translation,
    is_rtl_language,
)


class I18nConfigTests(TestCase):
    """国际化配置测试"""

    def test_supported_languages(self):
        """测试支持的语言"""
        self.assertEqual(len(SUPPORTED_LANGUAGES), 12)
        self.assertIn(('zh-cn', '中文 (简体)'), SUPPORTED_LANGUAGES)
        self.assertIn(('en', 'English'), SUPPORTED_LANGUAGES)

    def test_supported_currencies(self):
        """测试支持的货币"""
        self.assertIn('CNY', SUPPORTED_CURRENCIES)
        self.assertIn('USD', SUPPORTED_CURRENCIES)
        self.assertEqual(SUPPORTED_CURRENCIES['CNY']['symbol'], '¥')

    def test_supported_timezones(self):
        """测试支持的时区"""
        self.assertIn('Asia/Shanghai', SUPPORTED_TIMEZONES)
        self.assertIn('America/New_York', SUPPORTED_TIMEZONES)
        self.assertEqual(len(SUPPORTED_TIMEZONES), 10)

    def test_get_language_config(self):
        """测试获取语言配置"""
        config = get_language_config('zh-cn')
        self.assertIsNotNone(config)
        self.assertEqual(config['code'], 'zh-cn')
        self.assertEqual(config['currency'], 'CNY')
        self.assertEqual(config['timezone'], 'Asia/Shanghai')

    def test_get_currency_info(self):
        """测试获取货币信息"""
        info = get_currency_info('USD')
        self.assertIsNotNone(info)
        self.assertEqual(info['symbol'], '$')
        self.assertEqual(info['name'], '美元')
        self.assertEqual(info['decimal_places'], 2)

    def test_get_translation(self):
        """测试获取翻译"""
        translation_en = get_translation('hello', 'en')
        translation_cn = get_translation('hello', 'zh-cn')
        self.assertEqual(translation_en, 'Hello')
        self.assertEqual(translation_cn, '你好')

    def test_is_rtl_language(self):
        """测试 RTL 语言判断"""
        self.assertTrue(is_rtl_language('ar'))
        self.assertFalse(is_rtl_language('en'))
        self.assertFalse(is_rtl_language('zh-cn'))


class I18nManagerTests(TestCase):
    """国际化管理器测试"""

    def setUp(self):
        """设置测试"""
        self.manager = I18nManager('en', 'USD', 'America/New_York')

    def test_manager_initialization(self):
        """测试管理器初始化"""
        self.assertEqual(self.manager.language, 'en')
        self.assertEqual(self.manager.currency, 'USD')
        self.assertEqual(self.manager.timezone, 'America/New_York')

    def test_translate_english(self):
        """测试英文翻译"""
        result = self.manager.translate('hello')
        self.assertEqual(result, 'Hello')

    def test_translate_chinese(self):
        """测试中文翻译"""
        manager = I18nManager('zh-cn')
        result = manager.translate('hello')
        self.assertEqual(result, '你好')

    def test_translate_with_parameters(self):
        """测试带参数的翻译"""
        result = self.manager.translate('greeting', name='John')
        self.assertIsNotNone(result)

    def test_translate_missing_key(self):
        """测试缺失翻译键"""
        result = self.manager.translate('nonexistent_key')
        self.assertEqual(result, 'nonexistent_key')

    def test_convert_currency_same(self):
        """测试相同货币转换"""
        result = self.manager.convert_currency(Decimal('100'), 'USD', 'USD')
        self.assertEqual(result, Decimal('100'))

    def test_convert_currency_cny_to_usd(self):
        """测试 CNY 转 USD"""
        result = self.manager.convert_currency(Decimal('100'), 'CNY', 'USD')
        self.assertGreater(result, 0)
        self.assertLess(result, 100)

    def test_convert_currency_usd_to_cny(self):
        """测试 USD 转 CNY"""
        result = self.manager.convert_currency(Decimal('10'), 'USD', 'CNY')
        self.assertGreater(result, 10)

    def test_format_currency_usd(self):
        """测试 USD 货币格式化"""
        result = self.manager.format_currency(Decimal('1234.56'), 'USD')
        self.assertIn('$', result)
        self.assertIn('1234.56', result)

    def test_format_currency_cny(self):
        """测试 CNY 货币格式化"""
        result = self.manager.format_currency(Decimal('1234.56'), 'CNY')
        self.assertIn('¥', result)

    def test_convert_timezone(self):
        """测试时区转换"""
        dt = datetime(2024, 1, 15, 12, 0, 0)
        result = self.manager.convert_timezone(dt, 'Asia/Shanghai', 'America/New_York')
        self.assertIsNotNone(result)
        self.assertNotEqual(result.hour, 12)

    def test_convert_timezone_same(self):
        """测试相同时区转换"""
        dt = datetime(2024, 1, 15, 12, 0, 0)
        result = self.manager.convert_timezone(dt, 'Asia/Shanghai', 'Asia/Shanghai')
        self.assertEqual(result.hour, 12)

    def test_format_date_english(self):
        """测试英文日期格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = self.manager.format_date(dt, 'date')
        self.assertIn('01', result)  # 月份
        self.assertIn('15', result)  # 日期

    def test_format_date_chinese(self):
        """测试中文日期格式化"""
        manager = I18nManager('zh-cn')
        dt = datetime(2024, 1, 15)
        result = manager.format_date(dt, 'date')
        self.assertIn('2024年', result)
        self.assertIn('月', result)
        self.assertIn('日', result)

    def test_format_datetime(self):
        """测试日期时间格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = self.manager.format_date(dt, 'datetime')
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)

    def test_format_number_english(self):
        """测试英文数字格式化"""
        result = self.manager.format_number(1234567.89)
        self.assertIn(',', result)  # 千位分隔符

    def test_format_number_german(self):
        """测试德文数字格式化"""
        manager = I18nManager('de')
        result = manager.format_number(1234.56)
        self.assertIn('.', result)  # 德文使用句号作为千位分隔符
        self.assertIn(',', result)  # 德文使用逗号作为小数分隔符

    def test_get_language_info(self):
        """测试获取语言信息"""
        info = self.manager.get_language_info()
        self.assertIsNotNone(info)
        self.assertEqual(info['code'], 'en')

    def test_get_currency_symbol(self):
        """测试获取货币符号"""
        symbol = self.manager.get_currency_symbol('USD')
        self.assertEqual(symbol, '$')

    def test_get_currency_name(self):
        """测试获取货币名称"""
        name = self.manager.get_currency_name('USD')
        self.assertEqual(name, '美元')

    def test_is_rtl(self):
        """测试 RTL 判断"""
        self.assertFalse(self.manager.is_rtl())
        manager_ar = I18nManager('ar')
        self.assertTrue(manager_ar.is_rtl())

    def test_set_language(self):
        """测试设置语言"""
        self.manager.set_language('zh-cn')
        self.assertEqual(self.manager.language, 'zh-cn')

    def test_set_currency(self):
        """测试设置货币"""
        self.manager.set_currency('CNY')
        self.assertEqual(self.manager.currency, 'CNY')

    def test_set_timezone(self):
        """测试设置时区"""
        self.manager.set_timezone('Asia/Tokyo')
        self.assertEqual(self.manager.timezone, 'Asia/Tokyo')

    def test_get_statistics(self):
        """测试获取统计"""
        self.manager.translate('hello')
        self.manager.convert_currency(Decimal('100'), 'CNY', 'USD')
        stats = self.manager.get_statistics()
        self.assertGreater(stats['translations'], 0)
        self.assertGreater(stats['currency_conversions'], 0)


class I18nFactoryTests(TestCase):
    """国际化工厂测试"""

    def setUp(self):
        """设置测试"""
        I18nFactory.clear_cache()

    def test_factory_get_manager(self):
        """测试工厂获取管理器"""
        manager = I18nFactory.get_manager('en', 'USD', 'America/New_York')
        self.assertIsNotNone(manager)
        self.assertEqual(manager.language, 'en')

    def test_factory_singleton(self):
        """测试工厂单例"""
        manager1 = I18nFactory.get_manager('en', 'USD', 'America/New_York')
        manager2 = I18nFactory.get_manager('en', 'USD', 'America/New_York')
        self.assertIs(manager1, manager2)

    def test_factory_get_default_manager(self):
        """测试工厂获取默认管理器"""
        manager = I18nFactory.get_default_manager()
        self.assertIsNotNone(manager)
        self.assertEqual(manager.language, DEFAULT_LANGUAGE)

    def test_factory_clear_cache(self):
        """测试工厂清空缓存"""
        manager1 = I18nFactory.get_manager('en', 'USD', 'America/New_York')
        I18nFactory.clear_cache()
        manager2 = I18nFactory.get_manager('en', 'USD', 'America/New_York')
        self.assertIsNot(manager1, manager2)


class I18nAPITests(APITestCase):
    """国际化 API 测试"""

    def setUp(self):
        """设置测试"""
        self.client = APIClient()

    def test_languages_endpoint(self):
        """测试语言列表端点"""
        response = self.client.get('/api/i18n/languages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertGreater(response.data['count'], 0)

    def test_currencies_endpoint(self):
        """测试货币列表端点"""
        response = self.client.get('/api/i18n/currencies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertGreater(response.data['count'], 0)

    def test_timezones_endpoint(self):
        """测试时区列表端点"""
        response = self.client.get('/api/i18n/timezones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertGreater(response.data['count'], 0)

    def test_translate_endpoint(self):
        """测试翻译端点"""
        response = self.client.post('/api/i18n/translate/', {
            'key': 'hello',
            'language': 'en',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['translation'], 'Hello')

    def test_convert_currency_endpoint(self):
        """测试货币转换端点"""
        response = self.client.post('/api/i18n/convert-currency/', {
            'amount': 100,
            'from_currency': 'CNY',
            'to_currency': 'USD',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('converted_amount', response.data)

    def test_format_currency_endpoint(self):
        """测试货币格式化端点"""
        response = self.client.post('/api/i18n/format-currency/', {
            'amount': 1234.56,
            'currency': 'USD',
            'language': 'en',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('formatted', response.data)

    def test_convert_timezone_endpoint(self):
        """测试时区转换端点"""
        response = self.client.post('/api/i18n/convert-timezone/', {
            'datetime': '2024-01-15T12:00:00',
            'from_timezone': 'Asia/Shanghai',
            'to_timezone': 'America/New_York',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('converted_datetime', response.data)

    def test_format_date_endpoint(self):
        """测试日期格式化端点"""
        response = self.client.post('/api/i18n/format-date/', {
            'datetime': '2024-01-15T12:00:00',
            'language': 'en',
            'format_type': 'date',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('formatted', response.data)

    def test_format_number_endpoint(self):
        """测试数字格式化端点"""
        response = self.client.post('/api/i18n/format-number/', {
            'number': 1234567.89,
            'language': 'en',
            'decimal_places': 2,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('formatted', response.data)

    def test_info_endpoint(self):
        """测试信息端点"""
        response = self.client.get('/api/i18n/info/?language=en')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertIn('statistics', response.data)


class I18nIntegrationTests(TestCase):
    """国际化集成测试"""

    def test_complete_workflow(self):
        """测试完整工作流程"""
        manager = get_i18n_manager('zh-cn', 'CNY', 'Asia/Shanghai')
        
        # 翻译
        hello = manager.translate('hello')
        self.assertEqual(hello, '你好')
        
        # 货币转换和格式化
        usd_amount = manager.convert_currency(Decimal('1000'), 'CNY', 'USD')
        formatted = manager.format_currency(usd_amount, 'USD')
        self.assertIn('$', formatted)
        
        # 时区转换和日期格式化
        dt = datetime(2024, 1, 15, 12, 0, 0)
        ny_time = manager.convert_timezone(dt, 'Asia/Shanghai', 'America/New_York')
        formatted_date = manager.format_date(ny_time)
        self.assertIsNotNone(formatted_date)

    def test_multi_language_support(self):
        """测试多语言支持"""
        for code, _ in SUPPORTED_LANGUAGES:
            manager = get_i18n_manager(language=code)
            result = manager.translate('hello')
            self.assertIsNotNone(result)

    def test_all_currencies_conversion(self):
        """测试所有货币转换"""
        manager = get_i18n_manager()
        amount = Decimal('100')
        
        currencies = list(SUPPORTED_CURRENCIES.keys())
        for from_curr in currencies[:3]:  # 测试前 3 个
            for to_curr in currencies[:3]:
                if from_curr != to_curr:
                    result = manager.convert_currency(amount, from_curr, to_curr)
                    self.assertIsNotNone(result)


class I18nPerformanceTests(TestCase):
    """国际化性能测试"""

    def test_translation_performance(self):
        """测试翻译性能"""
        import time
        manager = get_i18n_manager('en')
        
        start = time.time()
        for _ in range(100):
            manager.translate('hello')
        elapsed = time.time() - start
        
        # 应该在 0.1 秒内完成
        self.assertLess(elapsed, 0.1)

    def test_currency_conversion_performance(self):
        """测试货币转换性能"""
        import time
        manager = get_i18n_manager()
        
        start = time.time()
        for _ in range(100):
            manager.convert_currency(Decimal('100'), 'CNY', 'USD')
        elapsed = time.time() - start
        
        # 应该在 0.1 秒内完成
        self.assertLess(elapsed, 0.1)

    def test_formatting_performance(self):
        """测试格式化性能"""
        import time
        manager = get_i18n_manager('en')
        dt = datetime.now()
        
        start = time.time()
        for _ in range(100):
            manager.format_date(dt)
            manager.format_number(1234567.89)
        elapsed = time.time() - start
        
        # 应该在 0.1 秒内完成
        self.assertLess(elapsed, 0.1)
