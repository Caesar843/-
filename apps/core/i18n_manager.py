"""
国际化/本地化管理器

处理多语言翻译、货币转换、时区转换、日期格式化等。
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Any
from functools import lru_cache
import pytz

from .i18n_config import (
    DEFAULT_LANGUAGE,
    DEFAULT_CURRENCY,
    DEFAULT_TIMEZONE,
    SUPPORTED_LANGUAGES,
    SUPPORTED_CURRENCIES,
    SUPPORTED_TIMEZONES,
    EXCHANGE_RATES,
    LANGUAGE_DEFAULT_CURRENCY,
    LANGUAGE_DEFAULT_TIMEZONE,
    DATE_FORMATS,
    NUMBER_FORMATS,
    TRANSLATIONS,
    RTL_LANGUAGES,
    get_language_config,
    get_currency_info,
    get_translation,
    get_date_format,
    get_number_format,
)

logger = logging.getLogger(__name__)


class I18nManager:
    """国际化/本地化管理器"""

    def __init__(self, language: str = DEFAULT_LANGUAGE, currency: str = DEFAULT_CURRENCY, 
                 timezone_str: str = DEFAULT_TIMEZONE):
        """初始化管理器"""
        self.language = language
        self.currency = currency
        self.timezone = timezone_str
        self._translation_cache = {}
        self._currency_cache = {}
        self._statistics = {
            'translations': 0,
            'currency_conversions': 0,
            'timezone_conversions': 0,
            'date_formats': 0,
        }

    def translate(self, key: str, **kwargs) -> str:
        """翻译字符串"""
        try:
            translation = get_translation(key, self.language)
            
            # 支持参数替换 (例如: {name})
            if kwargs:
                translation = translation.format(**kwargs)
            
            self._statistics['translations'] += 1
            return translation
        except Exception as e:
            logger.error(f"翻译失败 {key}: {e}")
            return key

    def convert_currency(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """货币转换"""
        try:
            if from_currency == to_currency:
                return amount
            
            # 验证货币代码
            if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
                raise ValueError(f"不支持的货币代码")
            
            # 先转换为 CNY，再转换为目标货币
            amount_in_cny = amount / Decimal(str(EXCHANGE_RATES.get(from_currency, 1)))
            result = amount_in_cny * Decimal(str(EXCHANGE_RATES.get(to_currency, 1)))
            
            self._statistics['currency_conversions'] += 1
            return result.quantize(Decimal('0.01'))
        except Exception as e:
            logger.error(f"货币转换失败: {e}")
            return amount

    def format_currency(self, amount: Decimal, currency: Optional[str] = None) -> str:
        """格式化货币"""
        try:
            currency_code = currency or self.currency
            currency_info = get_currency_info(currency_code)
            
            if not currency_info:
                return str(amount)
            
            symbol = currency_info['symbol']
            decimal_places = currency_info['decimal_places']
            
            # 格式化数字（货币通常不使用千位分隔符）
            number_format = get_number_format(self.language)
            decimal_sep = number_format['decimal_separator']
            
            formatted_str = f"{float(amount):.{decimal_places}f}"
            formatted = formatted_str.replace('.', decimal_sep)
            
            return f"{symbol} {formatted}"
        except Exception as e:
            logger.error(f"货币格式化失败: {e}")
            return str(amount)

    def convert_timezone(self, dt: datetime, from_tz: Optional[str] = None, 
                        to_tz: Optional[str] = None) -> datetime:
        """时区转换"""
        try:
            from_timezone = from_tz or self.timezone
            to_timezone = to_tz or self.timezone
            
            if from_timezone == to_timezone:
                return dt
            
            # 验证时区
            if from_timezone not in SUPPORTED_TIMEZONES or to_timezone not in SUPPORTED_TIMEZONES:
                raise ValueError(f"不支持的时区")
            
            # 转换时区
            from_tz_obj = pytz.timezone(from_timezone)
            to_tz_obj = pytz.timezone(to_timezone)
            
            if dt.tzinfo is None:
                dt = from_tz_obj.localize(dt)
            else:
                dt = dt.astimezone(from_tz_obj)
            
            result = dt.astimezone(to_tz_obj)
            self._statistics['timezone_conversions'] += 1
            return result
        except Exception as e:
            logger.error(f"时区转换失败: {e}")
            return dt

    def format_date(self, dt: datetime, format_type: str = 'date') -> str:
        """格式化日期"""
        try:
            date_format = get_date_format(self.language, format_type)
            result = dt.strftime(date_format)
            self._statistics['date_formats'] += 1
            return result
        except Exception as e:
            logger.error(f"日期格式化失败: {e}")
            return str(dt)

    def format_number(self, number: float, decimal_places: int = 2) -> str:
        """格式化数字"""
        try:
            number_format = get_number_format(self.language)
            thousands_sep = number_format['thousands_separator']
            decimal_sep = number_format['decimal_separator']
            
            # 格式化数字为字符串，保留指定的小数位数
            formatted_str = f"{float(number):.{decimal_places}f}"
            
            # 拆分整数部分和小数部分
            parts = formatted_str.split('.')
            integer_part = parts[0]
            decimal_part = parts[1] if len(parts) > 1 else ''
            
            # 只有在整数部分超过 3 位时才添加千位分隔符
            if len(integer_part.replace('-', '')) > 3:
                sign = '-' if integer_part.startswith('-') else ''
                integer_part = integer_part.lstrip('-')
                # 反向处理以添加分隔符
                parts_list = []
                for i, char in enumerate(reversed(integer_part)):
                    if i > 0 and i % 3 == 0:
                        parts_list.append(thousands_sep)
                    parts_list.append(char)
                integer_part = sign + ''.join(reversed(parts_list))
            
            # 替换小数分隔符
            if decimal_part:
                formatted = integer_part + decimal_sep + decimal_part
            else:
                formatted = integer_part
            
            return formatted
        except Exception as e:
            logger.error(f"数字格式化失败: {e}")
            return str(number)

    def get_language_info(self) -> Dict:
        """获取当前语言信息"""
        return get_language_config(self.language) or {
            'code': self.language,
            'name': self.language,
        }

    def get_currency_symbol(self, currency: Optional[str] = None) -> str:
        """获取货币符号"""
        currency_code = currency or self.currency
        currency_info = get_currency_info(currency_code)
        return currency_info['symbol'] if currency_info else ''

    def get_currency_name(self, currency: Optional[str] = None) -> str:
        """获取货币名称"""
        currency_code = currency or self.currency
        currency_info = get_currency_info(currency_code)
        return currency_info['name'] if currency_info else currency_code

    def is_rtl(self) -> bool:
        """判断是否是 RTL 语言"""
        return self.language in RTL_LANGUAGES

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return self._statistics.copy()

    def set_language(self, language: str) -> None:
        """设置语言"""
        if any(code == language for code, _ in SUPPORTED_LANGUAGES):
            self.language = language
        else:
            logger.warning(f"不支持的语言: {language}")

    def set_currency(self, currency: str) -> None:
        """设置货币"""
        if currency in SUPPORTED_CURRENCIES:
            self.currency = currency
        else:
            logger.warning(f"不支持的货币: {currency}")

    def set_timezone(self, timezone_str: str) -> None:
        """设置时区"""
        if timezone_str in SUPPORTED_TIMEZONES:
            self.timezone = timezone_str
        else:
            logger.warning(f"不支持的时区: {timezone_str}")


class I18nFactory:
    """国际化管理器工厂"""

    _instances = {}

    @classmethod
    def get_manager(cls, language: str = DEFAULT_LANGUAGE, 
                   currency: str = DEFAULT_CURRENCY,
                   timezone_str: str = DEFAULT_TIMEZONE) -> I18nManager:
        """获取或创建管理器"""
        key = f"{language}_{currency}_{timezone_str}"
        if key not in cls._instances:
            cls._instances[key] = I18nManager(language, currency, timezone_str)
        return cls._instances[key]

    @classmethod
    def get_default_manager(cls) -> I18nManager:
        """获取默认管理器"""
        return cls.get_manager()

    @classmethod
    def clear_cache(cls) -> None:
        """清空缓存"""
        cls._instances.clear()


def get_i18n_manager(language: str = DEFAULT_LANGUAGE,
                     currency: str = DEFAULT_CURRENCY,
                     timezone_str: str = DEFAULT_TIMEZONE) -> I18nManager:
    """获取国际化管理器"""
    return I18nFactory.get_manager(language, currency, timezone_str)
