"""Format solver output for plain displays, LaTeX clients, or Unicode text."""

import sympy
from sympy import S, oo

PLAIN, LATEX, PRETTY = "plain", "latex", "pretty"
FORMATS = (PLAIN, LATEX, PRETTY)

_X, _Y = sympy.symbols("x y")


def matrix_plain(matrix):
    return ";".join(
        ",".join(str(matrix[row, col]) for col in range(matrix.cols))
        for row in range(matrix.rows)
    )


def _bound(value):
    if value == oo:
        return "+oo"
    if value == -oo:
        return "-oo"
    return str(value)


def _set_plain(value):
    if value == S.Reals:
        return "x in R"
    if value == S.EmptySet:
        return "no solution"
    if isinstance(value, sympy.Interval):
        left = "(" if value.left_open else "["
        right = ")" if value.right_open else "]"
        return "{}{},{}{}".format(left, _bound(value.start), _bound(value.end), right)
    if isinstance(value, sympy.FiniteSet):
        return ", ".join(str(item) for item in value)
    if isinstance(value, sympy.Union):
        return " U ".join(_set_plain(part) for part in value.args)
    return str(value)


def _set_rich(value, fmt):
    if value == S.Reals:
        return r"\forall x \in \mathbb{R}" if fmt == LATEX else "∀x ∈ ℝ"
    if value == S.EmptySet:
        return r"\varnothing" if fmt == LATEX else "∅"
    return sympy.latex(value) if fmt == LATEX else sympy.pretty(value, use_unicode=True)


def _linear_system(solution, fmt):
    if solution == S.EmptySet:
        return {
            PLAIN: "no solution",
            LATEX: r"\varnothing",
            PRETTY: "∅",
        }[fmt]

    values = next(iter(solution))
    free = sorted(set().union(*(value.free_symbols for value in values)), key=str)
    pairs = [(symbol, value) for symbol, value in zip((_X, _Y), values) if symbol != value]
    free_names = ", ".join(map(str, free))
    if fmt == LATEX:
        text = r",\; ".join(
            "{} = {}".format(symbol, sympy.latex(value)) for symbol, value in pairs
        )
        return text + (r"\quad ({}\ \text{{free}})".format(free_names) if free else "")
    text = ", ".join("{}={}".format(symbol, value) for symbol, value in pairs)
    return text + (" ({} free)".format(free_names) if free else "")


def _factors(solution, fmt):
    number, factors = solution["n"], solution["factors"]
    if len(factors) == 1 and next(iter(factors.values())) == 1:
        if fmt == LATEX:
            return r"{}\ \text{{ is prime}}".format(number)
        return "{} is prime".format(number)
    items = sorted(factors.items())
    if fmt == LATEX:
        return r" \cdot ".join(
            "{}^{{{}}}".format(prime, exponent) if exponent > 1 else str(prime)
            for prime, exponent in items
        )
    return "*".join(
        "{}^{}".format(prime, exponent) if exponent > 1 else str(prime)
        for prime, exponent in items
    )


def _value(value, fmt):
    if fmt == LATEX:
        return sympy.latex(value)
    if fmt == PRETTY:
        return sympy.pretty(value, use_unicode=True)
    if isinstance(value, sympy.MatrixBase):
        return matrix_plain(value)
    return str(value)


def _dict_result(solution, fmt):
    if "msg" in solution:
        return solution["msg"]
    if "factors" in solution:
        return _factors(solution, fmt)
    output = _value(solution.get("res", ""), fmt)
    if "evaluated" in solution:
        separator = "=" if fmt != LATEX else " = "
        output += separator + _value(solution["evaluated"], fmt)
    return output


def format_solution(request_type, solution, fmt=PLAIN):
    """Format the solver's ``sol`` value for the requested output format."""
    if fmt not in FORMATS:
        raise ValueError("Invalid format: {}".format(fmt))
    if isinstance(solution, dict):
        return _dict_result(solution, fmt)
    if request_type == "lin_system":
        return _linear_system(solution, fmt)
    return _set_plain(solution) if fmt == PLAIN else _set_rich(solution, fmt)
