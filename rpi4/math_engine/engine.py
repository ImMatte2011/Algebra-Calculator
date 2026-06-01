from rpi4.math_engine import parser, solver
from sympy import Integral, Derivative, simplify


def solve_expression(expr_str: str) -> str:
    parsed = parser.parse_input(expr_str)
    if "error" in parsed:
        return f"error: {parsed['error']}"

    # Do not handle integrals or derivatives — reject explicitly
    if parsed.get("type") == "expression":
        expr = parsed.get("value")
        try:
            if expr.has(Integral) or expr.has(Derivative):
                return "error: integrals and derivatives are not supported"
            # prefer a simplified form for expressions
            res = simplify(expr)
            return str(res)
        except Exception:
            result = solver.risolvi(parsed)
            if "error" in result:
                return f"error: {result['error']}"
            return str(result.get("sol"))

    # For equations/inequalities, use the solver and stringify
    result = solver.risolvi(parsed)
    if "error" in result:
        return f"error: {result['error']}"
    return str(result.get("sol"))
