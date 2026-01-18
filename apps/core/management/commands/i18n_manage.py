"""
国际化管理命令

管理多语言、货币、时区等配置。
"""

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime
from decimal import Decimal
import json
from tabulate import tabulate
from colorama import Fore, Style

from apps.core.i18n_manager import get_i18n_manager
from apps.core.i18n_config import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_CURRENCIES,
    SUPPORTED_TIMEZONES,
    DEFAULT_LANGUAGE,
    DEFAULT_CURRENCY,
    DEFAULT_TIMEZONE,
)


class Command(BaseCommand):
    """i18n 管理命令"""
    
    help = '国际化管理工具'

    def add_arguments(self, parser):
        """添加命令参数"""
        parser.add_argument('--list-languages', action='store_true', help='列出所有支持的语言')
        parser.add_argument('--list-currencies', action='store_true', help='列出所有支持的货币')
        parser.add_argument('--list-timezones', action='store_true', help='列出所有支持的时区')
        
        parser.add_argument('--translate', type=str, help='翻译字符串')
        parser.add_argument('--language', type=str, default=DEFAULT_LANGUAGE, help='目标语言')
        
        parser.add_argument('--convert-currency', type=float, help='要转换的金额')
        parser.add_argument('--from-currency', type=str, default=DEFAULT_CURRENCY, help='源货币')
        parser.add_argument('--to-currency', type=str, default=DEFAULT_CURRENCY, help='目标货币')
        
        parser.add_argument('--format-currency', type=float, help='要格式化的金额')
        parser.add_argument('--currency', type=str, default=DEFAULT_CURRENCY, help='货币代码')
        
        parser.add_argument('--convert-timezone', type=str, help='日期时间 (ISO format)')
        parser.add_argument('--from-timezone', type=str, default=DEFAULT_TIMEZONE, help='源时区')
        parser.add_argument('--to-timezone', type=str, default=DEFAULT_TIMEZONE, help='目标时区')
        
        parser.add_argument('--format-date', type=str, help='日期时间 (ISO format)')
        parser.add_argument('--format-type', type=str, default='date', help='格式类型 (date/datetime/time)')
        
        parser.add_argument('--format-number', type=float, help='要格式化的数字')
        parser.add_argument('--decimal-places', type=int, default=2, help='小数位数')
        
        parser.add_argument('--info', action='store_true', help='显示 i18n 信息')
        parser.add_argument('--test', action='store_true', help='测试系统连接')

    def handle(self, *args, **options):
        """处理命令"""
        try:
            if options['list_languages']:
                self._list_languages()
            elif options['list_currencies']:
                self._list_currencies()
            elif options['list_timezones']:
                self._list_timezones()
            elif options['translate']:
                self._translate(options)
            elif options['convert_currency']:
                self._convert_currency(options)
            elif options['format_currency']:
                self._format_currency(options)
            elif options['convert_timezone']:
                self._convert_timezone(options)
            elif options['format_date']:
                self._format_date(options)
            elif options['format_number']:
                self._format_number(options)
            elif options['info']:
                self._show_info(options)
            elif options['test']:
                self._test_system()
            else:
                self.stdout.write(self.style.WARNING('请指定一个选项。使用 --help 查看帮助。'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))

    def _list_languages(self):
        """列出所有支持的语言"""
        self.stdout.write(self.style.SUCCESS('\n✓ 支持的语言:'))
        
        headers = ['语言代码', '语言名称']
        data = [[code, name] for code, name in SUPPORTED_LANGUAGES]
        
        table = tabulate(data, headers=headers, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")
        self.stdout.write(self.style.SUCCESS(f'✓ 共 {len(SUPPORTED_LANGUAGES)} 种语言\n'))

    def _list_currencies(self):
        """列出所有支持的货币"""
        self.stdout.write(self.style.SUCCESS('\n✓ 支持的货币:'))
        
        headers = ['货币代码', '符号', '名称', '小数位']
        data = [
            [code, info['symbol'], info['name'], info['decimal_places']]
            for code, info in SUPPORTED_CURRENCIES.items()
        ]
        
        table = tabulate(data, headers=headers, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")
        self.stdout.write(self.style.SUCCESS(f'✓ 共 {len(SUPPORTED_CURRENCIES)} 种货币\n'))

    def _list_timezones(self):
        """列出所有支持的时区"""
        self.stdout.write(self.style.SUCCESS('\n✓ 支持的时区:'))
        
        headers = ['时区', '描述']
        data = [[tz, name] for tz, name in SUPPORTED_TIMEZONES.items()]
        
        table = tabulate(data, headers=headers, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")
        self.stdout.write(self.style.SUCCESS(f'✓ 共 {len(SUPPORTED_TIMEZONES)} 个时区\n'))

    def _translate(self, options):
        """翻译字符串"""
        key = options['translate']
        language = options['language']
        
        manager = get_i18n_manager(language=language)
        translation = manager.translate(key)
        
        self.stdout.write(self.style.SUCCESS('\n✓ 翻译结果:'))
        
        data = [
            ['键', key],
            ['语言', language],
            ['翻译', translation],
        ]
        
        table = tabulate(data, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")

    def _convert_currency(self, options):
        """货币转换"""
        amount = Decimal(str(options['convert_currency']))
        from_currency = options['from_currency']
        to_currency = options['to_currency']
        
        manager = get_i18n_manager()
        result = manager.convert_currency(amount, from_currency, to_currency)
        
        self.stdout.write(self.style.SUCCESS('\n✓ 货币转换结果:'))
        
        data = [
            ['原金额', f"{amount} {from_currency}"],
            ['转换为', f"{result} {to_currency}"],
            ['汇率', f"1 {from_currency} = ? {to_currency}"],
        ]
        
        table = tabulate(data, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")

    def _format_currency(self, options):
        """格式化货币"""
        amount = Decimal(str(options['format_currency']))
        currency = options['currency']
        language = options['language']
        
        manager = get_i18n_manager(language=language, currency=currency)
        formatted = manager.format_currency(amount, currency)
        
        self.stdout.write(self.style.SUCCESS('\n✓ 货币格式化结果:'))
        
        data = [
            ['原值', str(amount)],
            ['货币', currency],
            ['语言', language],
            ['格式化', formatted],
        ]
        
        table = tabulate(data, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")

    def _convert_timezone(self, options):
        """时区转换"""
        datetime_str = options['convert_timezone']
        from_tz = options['from_timezone']
        to_tz = options['to_timezone']
        
        try:
            dt = datetime.fromisoformat(datetime_str)
            manager = get_i18n_manager(timezone_str=from_tz)
            result = manager.convert_timezone(dt, from_tz, to_tz)
            
            self.stdout.write(self.style.SUCCESS('\n✓ 时区转换结果:'))
            
            data = [
                ['原时间', str(dt)],
                ['源时区', from_tz],
                ['目标时区', to_tz],
                ['转换后', str(result)],
            ]
            
            table = tabulate(data, tablefmt='grid')
            self.stdout.write(f"\n{table}\n")
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f'✗ 日期时间格式错误: {e}'))

    def _format_date(self, options):
        """格式化日期"""
        datetime_str = options['format_date']
        language = options['language']
        format_type = options['format_type']
        
        try:
            dt = datetime.fromisoformat(datetime_str)
            manager = get_i18n_manager(language=language)
            formatted = manager.format_date(dt, format_type)
            
            self.stdout.write(self.style.SUCCESS('\n✓ 日期格式化结果:'))
            
            data = [
                ['原值', str(dt)],
                ['语言', language],
                ['格式类型', format_type],
                ['格式化', formatted],
            ]
            
            table = tabulate(data, tablefmt='grid')
            self.stdout.write(f"\n{table}\n")
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f'✗ 日期时间格式错误: {e}'))

    def _format_number(self, options):
        """格式化数字"""
        number = float(options['format_number'])
        language = options['language']
        decimal_places = options['decimal_places']
        
        manager = get_i18n_manager(language=language)
        formatted = manager.format_number(number, decimal_places)
        
        self.stdout.write(self.style.SUCCESS('\n✓ 数字格式化结果:'))
        
        data = [
            ['原值', str(number)],
            ['语言', language],
            ['小数位', str(decimal_places)],
            ['格式化', formatted],
        ]
        
        table = tabulate(data, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")

    def _show_info(self, options):
        """显示 i18n 信息"""
        language = options['language']
        manager = get_i18n_manager(language=language)
        
        self.stdout.write(self.style.SUCCESS('\n✓ 国际化信息:'))
        
        data = [
            ['语言', manager.language],
            ['货币', manager.currency],
            ['时区', manager.timezone],
            ['RTL 语言', '是' if manager.is_rtl() else '否'],
            ['翻译次数', manager._statistics['translations']],
            ['货币转换次数', manager._statistics['currency_conversions']],
            ['时区转换次数', manager._statistics['timezone_conversions']],
            ['日期格式化次数', manager._statistics['date_formats']],
        ]
        
        table = tabulate(data, tablefmt='grid')
        self.stdout.write(f"\n{table}\n")

    def _test_system(self):
        """测试系统"""
        self.stdout.write(self.style.SUCCESS('\n✓ 开始测试国际化系统...\n'))
        
        try:
            # 测试翻译
            self.stdout.write('测试翻译...')
            manager = get_i18n_manager('en')
            result = manager.translate('hello')
            self.stdout.write(self.style.SUCCESS(f'✓ 翻译成功: {result}'))
            
            # 测试货币转换
            self.stdout.write('测试货币转换...')
            result = manager.convert_currency(Decimal('100'), 'CNY', 'USD')
            self.stdout.write(self.style.SUCCESS(f'✓ 货币转换成功: 100 CNY = {result} USD'))
            
            # 测试时区转换
            self.stdout.write('测试时区转换...')
            dt = datetime.now()
            result = manager.convert_timezone(dt, 'Asia/Shanghai', 'America/New_York')
            self.stdout.write(self.style.SUCCESS(f'✓ 时区转换成功: {result}'))
            
            # 测试日期格式化
            self.stdout.write('测试日期格式化...')
            result = manager.format_date(dt)
            self.stdout.write(self.style.SUCCESS(f'✓ 日期格式化成功: {result}'))
            
            # 测试数字格式化
            self.stdout.write('测试数字格式化...')
            result = manager.format_number(1234.56)
            self.stdout.write(self.style.SUCCESS(f'✓ 数字格式化成功: {result}'))
            
            self.stdout.write(self.style.SUCCESS('\n✓ 所有测试通过!\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 测试失败: {e}'))
