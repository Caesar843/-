"""
Custom template filters used across the project.
"""

from django import template

register = template.Library()


@register.filter(name='sum')
def sum_filter(values, field=None):
    """
    Sum iterable values or a field on each item.

    Usage:
        {{ values|sum }}
        {{ objects|sum:"field" }}
    """
    if values is None:
        return 0

    try:
        iterator = list(values)
    except TypeError:
        return 0

    total = 0
    for item in iterator:
        if field:
            if isinstance(item, dict):
                value = item.get(field, 0)
            else:
                value = getattr(item, field, 0)
        else:
            value = item

        if value is None:
            value = 0

        total += value

    return total
