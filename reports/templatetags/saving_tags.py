from decimal import Decimal

from django import template
from django.templatetags.static import static

register = template.Library()


@register.filter
def money_minor(value, currency="BRL"):
    try:
        amount = Decimal(value) / Decimal(100)
    except (TypeError, ValueError, ArithmeticError):
        amount = Decimal(0)
    return f"{'R$' if currency == 'BRL' else currency} {format_decimal(amount, 2)}"


@register.filter
def money(value, currency="BRL"):
    try:
        amount = Decimal(value)
    except (TypeError, ValueError, ArithmeticError):
        amount = Decimal(0)
    return f"{'R$' if currency == 'BRL' else currency} {format_decimal(amount, 2)}"


@register.filter
def decimal(value, places=2):
    try:
        return format_decimal(Decimal(value), int(places))
    except (TypeError, ValueError, ArithmeticError):
        return "—"


@register.filter
def scaled(value, places=8):
    try:
        return format_decimal(Decimal(value) / (Decimal(10) ** int(places)), int(places))
    except (TypeError, ValueError, ArithmeticError):
        return "—"


@register.simple_tag
def static_url(path):
    return static(path)


def format_decimal(value, places):
    formatted = f"{value:,.{places}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")
