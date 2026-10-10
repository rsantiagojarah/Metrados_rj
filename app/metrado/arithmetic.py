"""Bounded arithmetic only: no names, calls, attributes or Python execution."""
import ast
from decimal import Decimal, DecimalException, Underflow, localcontext
import re

_NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z')
HELP = 'Admite +, -, *, /, ^ y paréntesis. Se guarda solo el resultado.'


def numeric_text(text, *, positive=False, nonnegative=False, nonzero=False, integer=False, allow_blank=False):
    original = str(text).strip()
    if not original and allow_blank:
        return ''
    source = original.replace(',', '.').replace('^', '**')
    if not source or len(source) > 512 or not re.fullmatch(r'[0-9.eE+*/()\s-]+', source):
        raise ValueError('Introduce un número o una operación con +, -, *, /, ^ y paréntesis.')
    try:
        literal = bool(_NUMBER.fullmatch(source))
        tree = None if literal else ast.parse(source, mode='eval')
        if tree is not None and sum(1 for _ in ast.walk(tree)) > 128:
            raise ValueError('La operación es demasiado larga.')

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                value = Decimal(ast.get_source_segment(source, node))
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = visit(node.operand)
                if isinstance(node.op, ast.USub):
                    value = -value
            elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Add):
                    value = left + right
                elif isinstance(node.op, ast.Sub):
                    value = left - right
                elif isinstance(node.op, ast.Mult):
                    value = left * right
                elif isinstance(node.op, ast.Div):
                    if right == 0:
                        raise ValueError('No se puede dividir entre cero.')
                    value = left / right
                else:
                    if abs(right) > 10000:
                        raise ValueError('El exponente está fuera del rango permitido.')
                    value = left ** right
            else:
                raise ValueError('Solo se admiten operaciones aritméticas.')
            if not value.is_finite() or abs(value) > Decimal('1e308'):
                raise ValueError('El resultado está fuera del rango permitido.')
            return value

        with localcontext() as context:
            context.prec = 28
            context.Emax = 308
            context.Emin = -308
            context.traps[Underflow] = True
            value = Decimal(source) if literal else visit(tree.body)
            if not value.is_finite() or abs(value) > Decimal('1e308'):
                raise ValueError('El resultado está fuera del rango permitido.')
            if positive and value <= 0:
                raise ValueError('El resultado debe ser positivo.')
            if nonnegative and value < 0:
                raise ValueError('El resultado no puede ser negativo.')
            if nonzero and value == 0:
                raise ValueError('El resultado no puede ser cero.')
            if integer and value != value.to_integral_value():
                raise ValueError('El resultado debe ser un número entero.')
            if value and float(value) == 0:
                raise ValueError('El resultado es demasiado pequeño.')
            if literal:
                return original
            normalized = value.normalize()
            return format(normalized, 'f') if -15 <= value.adjusted() <= 20 else str(normalized)
    except (SyntaxError, DecimalException, RecursionError, OverflowError) as error:
        raise ValueError('Operación inválida o resultado fuera del rango permitido.') from error
