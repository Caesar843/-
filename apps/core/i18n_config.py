"""
国际化/本地化配置管理

支持多语言、多货币、时区处理和日期格式化。
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

# 支持的语言列表
SUPPORTED_LANGUAGES = [
    ('zh-cn', '中文 (简体)'),
    ('zh-hk', '中文 (繁体)'),
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'Français'),
    ('de', 'Deutsch'),
    ('ja', '日本語'),
    ('ko', '한국어'),
    ('ru', 'Русский'),
    ('pt', 'Português'),
    ('ar', 'العربية'),
    ('hi', 'हिन्दी'),
]

# 默认语言
DEFAULT_LANGUAGE = 'zh-cn'
DEFAULT_TIMEZONE = 'Asia/Shanghai'
DEFAULT_CURRENCY = 'CNY'

# 支持的时区
SUPPORTED_TIMEZONES = {
    'Asia/Shanghai': '中国 (北京)',
    'America/New_York': '美国 (纽约)',
    'America/Los_Angeles': '美国 (洛杉矶)',
    'Europe/London': '英国 (伦敦)',
    'Europe/Paris': '法国 (巴黎)',
    'Europe/Berlin': '德国 (柏林)',
    'Asia/Tokyo': '日本 (东京)',
    'Asia/Seoul': '韩国 (首尔)',
    'Asia/Dubai': '阿联酋 (迪拜)',
    'Australia/Sydney': '澳大利亚 (悉尼)',
}

# 支持的货币
SUPPORTED_CURRENCIES = {
    'CNY': {'symbol': '¥', 'name': '人民币', 'decimal_places': 2},
    'USD': {'symbol': '$', 'name': '美元', 'decimal_places': 2},
    'EUR': {'symbol': '€', 'name': '欧元', 'decimal_places': 2},
    'GBP': {'symbol': '£', 'name': '英镑', 'decimal_places': 2},
    'JPY': {'symbol': '¥', 'name': '日元', 'decimal_places': 0},
    'KRW': {'symbol': '₩', 'name': '韩元', 'decimal_places': 0},
    'INR': {'symbol': '₹', 'name': '印度卢比', 'decimal_places': 2},
    'RUB': {'symbol': '₽', 'name': '俄罗斯卢布', 'decimal_places': 2},
    'AED': {'symbol': 'د.إ', 'name': '阿联酋迪拉姆', 'decimal_places': 2},
    'AUD': {'symbol': 'A$', 'name': '澳大利亚元', 'decimal_places': 2},
}

# 汇率配置（相对于 CNY）
EXCHANGE_RATES = {
    'CNY': 1.0,
    'USD': 0.14,  # 1 CNY = 0.14 USD
    'EUR': 0.13,  # 1 CNY = 0.13 EUR
    'GBP': 0.11,
    'JPY': 15.0,
    'KRW': 175.0,
    'INR': 11.5,
    'RUB': 13.0,
    'AED': 0.51,
    'AUD': 0.21,
}

# 语言对应的货币
LANGUAGE_DEFAULT_CURRENCY = {
    'zh-cn': 'CNY',
    'zh-hk': 'HKD',
    'en': 'USD',
    'es': 'EUR',
    'fr': 'EUR',
    'de': 'EUR',
    'ja': 'JPY',
    'ko': 'KRW',
    'ru': 'RUB',
    'pt': 'EUR',
    'ar': 'AED',
    'hi': 'INR',
}

# 语言对应的时区
LANGUAGE_DEFAULT_TIMEZONE = {
    'zh-cn': 'Asia/Shanghai',
    'en': 'America/New_York',
    'es': 'Europe/Madrid',
    'fr': 'Europe/Paris',
    'de': 'Europe/Berlin',
    'ja': 'Asia/Tokyo',
    'ko': 'Asia/Seoul',
    'ru': 'Europe/Moscow',
    'pt': 'Europe/Lisbon',
    'ar': 'Asia/Dubai',
    'hi': 'Asia/Kolkata',
}

# 日期格式配置
DATE_FORMATS = {
    'zh-cn': {'date': '%Y年%m月%d日', 'datetime': '%Y年%m月%d日 %H:%M:%S', 'time': '%H:%M:%S'},
    'zh-hk': {'date': '%Y年%m月%d日', 'datetime': '%Y年%m月%d日 %H:%M:%S', 'time': '%H:%M:%S'},
    'en': {'date': '%m/%d/%Y', 'datetime': '%m/%d/%Y %I:%M:%S %p', 'time': '%I:%M:%S %p'},
    'es': {'date': '%d/%m/%Y', 'datetime': '%d/%m/%Y %H:%M:%S', 'time': '%H:%M:%S'},
    'fr': {'date': '%d/%m/%Y', 'datetime': '%d/%m/%Y %H:%M:%S', 'time': '%H:%M:%S'},
    'de': {'date': '%d.%m.%Y', 'datetime': '%d.%m.%Y %H:%M:%S', 'time': '%H:%M:%S'},
    'ja': {'date': '%Y年%m月%d日', 'datetime': '%Y年%m月%d日 %H:%M:%S', 'time': '%H:%M:%S'},
    'ko': {'date': '%Y년 %m월 %d일', 'datetime': '%Y년 %m월 %d일 %H:%M:%S', 'time': '%H:%M:%S'},
    'ru': {'date': '%d.%m.%Y', 'datetime': '%d.%m.%Y %H:%M:%S', 'time': '%H:%M:%S'},
    'pt': {'date': '%d/%m/%Y', 'datetime': '%d/%m/%Y %H:%M:%S', 'time': '%H:%M:%S'},
    'ar': {'date': '%d/%m/%Y', 'datetime': '%d/%m/%Y %H:%M:%S', 'time': '%H:%M:%S'},
    'hi': {'date': '%d/%m/%Y', 'datetime': '%d/%m/%Y %H:%M:%S', 'time': '%H:%M:%S'},
}

# 数字格式配置
NUMBER_FORMATS = {
    'zh-cn': {'thousands_separator': ',', 'decimal_separator': '.'},
    'en': {'thousands_separator': ',', 'decimal_separator': '.'},
    'de': {'thousands_separator': '.', 'decimal_separator': ','},
    'fr': {'thousands_separator': ' ', 'decimal_separator': ','},
    'es': {'thousands_separator': '.', 'decimal_separator': ','},
    'ru': {'thousands_separator': ' ', 'decimal_separator': ','},
    'pt': {'thousands_separator': '.', 'decimal_separator': ','},
    'ja': {'thousands_separator': ',', 'decimal_separator': '.'},
    'ko': {'thousands_separator': ',', 'decimal_separator': '.'},
    'ar': {'thousands_separator': '٬', 'decimal_separator': '٫'},
    'hi': {'thousands_separator': ',', 'decimal_separator': '.'},
}

# 翻译字典（示例）
TRANSLATIONS = {
    'greeting': {
        'zh-cn': '欢迎',
        'en': 'Welcome',
        'es': 'Bienvenido',
        'fr': 'Bienvenue',
        'de': 'Willkommen',
        'ja': 'ようこそ',
        'ko': '환영합니다',
        'ru': 'Добро пожаловать',
    },
    'goodbye': {
        'zh-cn': '再见',
        'en': 'Goodbye',
        'es': 'Adiós',
        'fr': 'Au revoir',
        'de': 'Auf Wiedersehen',
        'ja': 'さようなら',
        'ko': '안녕히 가세요',
        'ru': 'До свидания',
    },
    'hello': {
        'zh-cn': '你好',
        'en': 'Hello',
        'es': 'Hola',
        'fr': 'Bonjour',
        'de': 'Hallo',
        'ja': 'こんにちは',
        'ko': '안녕하세요',
        'ru': 'Привет',
    },
    'thank_you': {
        'zh-cn': '谢谢',
        'en': 'Thank you',
        'es': 'Gracias',
        'fr': 'Merci',
        'de': 'Danke',
        'ja': 'ありがとう',
        'ko': '감사합니다',
        'ru': 'Спасибо',
    },
}

# RTL（从右到左）语言
RTL_LANGUAGES = ['ar', 'he']

# i18n 缓存配置
I18N_CACHE_CONFIG = {
    'enabled': True,
    'ttl': 3600,  # 1 小时
    'max_entries': 10000,
}

# i18n 监控配置
I18N_MONITORING_CONFIG = {
    'enabled': True,
    'log_missing_translations': True,
    'log_currency_conversions': True,
    'performance_threshold': 100,  # ms
}


def get_language_config(language_code: str) -> Dict:
    """获取语言配置"""
    for code, name in SUPPORTED_LANGUAGES:
        if code == language_code:
            return {
                'code': code,
                'name': name,
                'currency': LANGUAGE_DEFAULT_CURRENCY.get(code, DEFAULT_CURRENCY),
                'timezone': LANGUAGE_DEFAULT_TIMEZONE.get(code, DEFAULT_TIMEZONE),
                'is_rtl': language_code in RTL_LANGUAGES,
            }
    return None


def get_currency_info(currency_code: str) -> Optional[Dict]:
    """获取货币信息"""
    return SUPPORTED_CURRENCIES.get(currency_code)


def get_timezone_info(timezone: str) -> Optional[str]:
    """获取时区信息"""
    return SUPPORTED_TIMEZONES.get(timezone)


def get_translation(key: str, language_code: str) -> str:
    """获取翻译"""
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(language_code, TRANSLATIONS[key].get(DEFAULT_LANGUAGE, key))
    return key


def get_date_format(language_code: str, format_type: str = 'date') -> str:
    """获取日期格式"""
    formats = DATE_FORMATS.get(language_code, DATE_FORMATS[DEFAULT_LANGUAGE])
    return formats.get(format_type, '%Y-%m-%d')


def get_number_format(language_code: str) -> Dict:
    """获取数字格式"""
    return NUMBER_FORMATS.get(language_code, NUMBER_FORMATS[DEFAULT_LANGUAGE])


def is_rtl_language(language_code: str) -> bool:
    """判断是否是 RTL 语言"""
    return language_code in RTL_LANGUAGES


def get_enabled_languages() -> List[Tuple[str, str]]:
    """获取所有启用的语言"""
    return SUPPORTED_LANGUAGES


def get_currency_list() -> List[str]:
    """获取所有支持的货币"""
    return list(SUPPORTED_CURRENCIES.keys())


def get_timezone_list() -> List[str]:
    """获取所有支持的时区"""
    return list(SUPPORTED_TIMEZONES.keys())
