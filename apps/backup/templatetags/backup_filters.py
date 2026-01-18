from django import template

register = template.Library()


@register.filter
def div(value, divisor):
    """
    将数值除以指定的除数
    用法: {{ value|div:1048576 }}
    """
    try:
        return int(value) // int(divisor)
    except (ValueError, TypeError, ZeroDivisionError):
        return value
