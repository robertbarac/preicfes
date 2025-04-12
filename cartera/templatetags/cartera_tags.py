from django import template
from calendar import month_name

register = template.Library()

@register.filter(name='subtract')
def subtract(value, arg):
    """Resta el argumento del valor"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def absolute(value):
    return abs(value)

@register.filter(name='get_month_name')
def get_month_name(month_number):
    """Convierte número de mes a nombre (1 -> 'Enero')"""
    try:
        return month_name[month_number]
    except (IndexError, KeyError):
        return str(month_number)