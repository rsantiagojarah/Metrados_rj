"""Shared visible-number formatting for Metrados and spreadsheet reports."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


TWO_DECIMALS = Decimal('0.01')


def format_two_decimals(value):
    """Format a finite numeric value as Excel visibly does with ``0.00``.

    ``str`` keeps the decimal value intended by a user or returned by the engine,
    instead of exposing a binary floating-point representation such as
    343.21499999999997 to the presentation layer.
    """
    try:
        number = Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, ValueError) as error:
        raise ValueError('El valor mostrado debe ser numérico.') from error
    if not number.is_finite():
        raise ValueError('El valor mostrado debe ser finito.')
    return format(number.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP), '.2f')
