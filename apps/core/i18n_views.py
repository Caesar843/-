"""
国际化 REST API 视图

提供国际化功能的 REST 接口。
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
import logging

from .i18n_manager import get_i18n_manager
from .i18n_config import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_CURRENCIES,
    SUPPORTED_TIMEZONES,
    DEFAULT_LANGUAGE,
    DEFAULT_CURRENCY,
    DEFAULT_TIMEZONE,
    LANGUAGE_DEFAULT_CURRENCY,
    LANGUAGE_DEFAULT_TIMEZONE,
    get_enabled_languages,
    get_currency_list,
    get_timezone_list,
)

logger = logging.getLogger(__name__)


class I18nViewSet(viewsets.ViewSet):
    """国际化 ViewSet"""
    
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='languages')
    def languages(self, request):
        """获取支持的语言列表"""
        try:
            languages = [
                {
                    'code': code,
                    'name': name,
                    'default_currency': LANGUAGE_DEFAULT_CURRENCY.get(code, DEFAULT_CURRENCY),
                    'default_timezone': LANGUAGE_DEFAULT_TIMEZONE.get(code, DEFAULT_TIMEZONE),
                }
                for code, name in get_enabled_languages()
            ]
            return Response({
                'status': 'success',
                'count': len(languages),
                'languages': languages,
            })
        except Exception as e:
            logger.error(f"获取语言列表失败: {e}")
            return Response(
                {'error': '获取语言列表失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='currencies')
    def currencies(self, request):
        """获取支持的货币列表"""
        try:
            currencies = [
                {
                    'code': code,
                    'symbol': SUPPORTED_CURRENCIES[code]['symbol'],
                    'name': SUPPORTED_CURRENCIES[code]['name'],
                    'decimal_places': SUPPORTED_CURRENCIES[code]['decimal_places'],
                }
                for code in get_currency_list()
            ]
            return Response({
                'status': 'success',
                'count': len(currencies),
                'currencies': currencies,
            })
        except Exception as e:
            logger.error(f"获取货币列表失败: {e}")
            return Response(
                {'error': '获取货币列表失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='timezones')
    def timezones(self, request):
        """获取支持的时区列表"""
        try:
            timezones = [
                {
                    'timezone': tz,
                    'name': SUPPORTED_TIMEZONES[tz],
                }
                for tz in get_timezone_list()
            ]
            return Response({
                'status': 'success',
                'count': len(timezones),
                'timezones': timezones,
            })
        except Exception as e:
            logger.error(f"获取时区列表失败: {e}")
            return Response(
                {'error': '获取时区列表失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='translate')
    def translate(self, request):
        """翻译字符串"""
        try:
            key = request.data.get('key')
            language = request.data.get('language', DEFAULT_LANGUAGE)
            
            if not key:
                return Response(
                    {'error': '缺少 key 参数'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            manager = get_i18n_manager(language=language)
            translation = manager.translate(key)
            
            return Response({
                'status': 'success',
                'key': key,
                'language': language,
                'translation': translation,
            })
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return Response(
                {'error': '翻译失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='convert-currency')
    def convert_currency(self, request):
        """货币转换"""
        try:
            try:
                amount = Decimal(str(request.data.get('amount', 0)))
            except (InvalidOperation, TypeError):
                return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
            from_currency = request.data.get('from_currency', DEFAULT_CURRENCY)
            to_currency = request.data.get('to_currency', DEFAULT_CURRENCY)
            if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
                return Response({'error': 'Unsupported currency'}, status=status.HTTP_400_BAD_REQUEST)
            
            manager = get_i18n_manager(currency=from_currency)
            result = manager.convert_currency(amount, from_currency, to_currency)
            
            return Response({
                'status': 'success',
                'amount': str(amount),
                'from_currency': from_currency,
                'to_currency': to_currency,
                'converted_amount': str(result),
            })
        except Exception as e:
            logger.error(f"货币转换失败: {e}")
            return Response(
                {'error': '货币转换失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='format-currency')
    def format_currency(self, request):
        """格式化货币"""
        try:
            try:
                amount = Decimal(str(request.data.get('amount', 0)))
            except (InvalidOperation, TypeError):
                return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
            currency = request.data.get('currency', DEFAULT_CURRENCY)
            language = request.data.get('language', DEFAULT_LANGUAGE)
            if currency not in SUPPORTED_CURRENCIES:
                return Response({'error': 'Unsupported currency'}, status=status.HTTP_400_BAD_REQUEST)
            
            manager = get_i18n_manager(language=language, currency=currency)
            formatted = manager.format_currency(amount, currency)
            
            return Response({
                'status': 'success',
                'amount': str(amount),
                'currency': currency,
                'language': language,
                'formatted': formatted,
            })
        except Exception as e:
            logger.error(f"货币格式化失败: {e}")
            return Response(
                {'error': '货币格式化失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='convert-timezone')
    def convert_timezone(self, request):
        """时区转换"""
        try:
            datetime_str = request.data.get('datetime')
            from_timezone = request.data.get('from_timezone', DEFAULT_TIMEZONE)
            to_timezone = request.data.get('to_timezone', DEFAULT_TIMEZONE)
            if from_timezone not in SUPPORTED_TIMEZONES or to_timezone not in SUPPORTED_TIMEZONES:
                return Response({'error': 'Unsupported timezone'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not datetime_str:
                return Response(
                    {'error': '缺少 datetime 参数'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 解析日期时间
            try:
                dt = datetime.fromisoformat(datetime_str)
            except ValueError:
                return Response({'error': 'Invalid datetime format'}, status=status.HTTP_400_BAD_REQUEST)
            
            manager = get_i18n_manager(timezone_str=from_timezone)
            result = manager.convert_timezone(dt, from_timezone, to_timezone)
            
            return Response({
                'status': 'success',
                'datetime': datetime_str,
                'from_timezone': from_timezone,
                'to_timezone': to_timezone,
                'converted_datetime': result.isoformat(),
            })
        except Exception as e:
            logger.error(f"时区转换失败: {e}")
            return Response(
                {'error': '时区转换失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='format-date')
    def format_date(self, request):
        """格式化日期"""
        try:
            datetime_str = request.data.get('datetime')
            language = request.data.get('language', DEFAULT_LANGUAGE)
            format_type = request.data.get('format_type', 'date')  # date, datetime, time
            
            if not datetime_str:
                return Response(
                    {'error': '缺少 datetime 参数'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 解析日期时间
            try:
                dt = datetime.fromisoformat(datetime_str)
            except ValueError:
                return Response({'error': 'Invalid datetime format'}, status=status.HTTP_400_BAD_REQUEST)
            
            manager = get_i18n_manager(language=language)
            formatted = manager.format_date(dt, format_type)
            
            return Response({
                'status': 'success',
                'datetime': datetime_str,
                'language': language,
                'format_type': format_type,
                'formatted': formatted,
            })
        except Exception as e:
            logger.error(f"日期格式化失败: {e}")
            return Response(
                {'error': '日期格式化失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='format-number')
    def format_number(self, request):
        """格式化数字"""
        try:
            try:
                number = float(request.data.get('number', 0))
            except (TypeError, ValueError):
                return Response({'error': 'Invalid number'}, status=status.HTTP_400_BAD_REQUEST)
            language = request.data.get('language', DEFAULT_LANGUAGE)
            decimal_places = int(request.data.get('decimal_places', 2))
            
            manager = get_i18n_manager(language=language)
            formatted = manager.format_number(number, decimal_places)
            
            return Response({
                'status': 'success',
                'number': number,
                'language': language,
                'decimal_places': decimal_places,
                'formatted': formatted,
            })
        except Exception as e:
            logger.error(f"数字格式化失败: {e}")
            return Response(
                {'error': '数字格式化失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='info')
    def info(self, request):
        """获取 i18n 信息"""
        try:
            language = request.query_params.get('language', DEFAULT_LANGUAGE)
            manager = get_i18n_manager(language=language)
            
            return Response({
                'status': 'success',
                'language': manager.language,
                'currency': manager.currency,
                'timezone': manager.timezone,
                'language_info': manager.get_language_info(),
                'is_rtl': manager.is_rtl(),
                'statistics': manager.get_statistics(),
            })
        except Exception as e:
            logger.error(f"获取 i18n 信息失败: {e}")
            return Response(
                {'error': '获取 i18n 信息失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# 简单视图函数

def translate_view(request):
    """快速翻译视图"""
    from rest_framework.response import Response
    
    try:
        key = request.GET.get('key', 'hello')
        language = request.GET.get('language', DEFAULT_LANGUAGE)
        
        manager = get_i18n_manager(language=language)
        translation = manager.translate(key)
        
        return Response({
            'key': key,
            'language': language,
            'translation': translation,
        })
    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return Response({'error': '翻译失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def convert_currency_view(request):
    """快速货币转换视图"""
    from rest_framework.response import Response
    
    try:
        try:
            amount = Decimal(str(request.GET.get('amount', 100)))
        except (InvalidOperation, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        from_currency = request.GET.get('from', DEFAULT_CURRENCY)
        to_currency = request.GET.get('to', DEFAULT_CURRENCY)
        if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
            return Response({'error': 'Unsupported currency'}, status=status.HTTP_400_BAD_REQUEST)
        
        manager = get_i18n_manager()
        result = manager.convert_currency(amount, from_currency, to_currency)
        
        return Response({
            'amount': str(amount),
            'from': from_currency,
            'to': to_currency,
            'result': str(result),
        })
    except Exception as e:
        logger.error(f"货币转换失败: {e}")
        return Response({'error': '货币转换失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def format_date_view(request):
    """快速日期格式化视图"""
    from rest_framework.response import Response
    
    try:
        datetime_str = request.GET.get('datetime', datetime.now().isoformat())
        language = request.GET.get('language', DEFAULT_LANGUAGE)
        
        try:
            dt = datetime.fromisoformat(datetime_str)
        except ValueError:
            return Response({'error': 'Invalid datetime format'}, status=status.HTTP_400_BAD_REQUEST)
        manager = get_i18n_manager(language=language)
        formatted = manager.format_date(dt)
        
        return Response({
            'datetime': datetime_str,
            'language': language,
            'formatted': formatted,
        })
    except Exception as e:
        logger.error(f"日期格式化失败: {e}")
        return Response({'error': '日期格式化失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
