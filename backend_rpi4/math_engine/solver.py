from __future__ import annotations

from typing import Any, Dict

import sympy
from sympy import S, expand, factor, simplify, solveset, symbols
from sympy.calculus.util import continuous_domain
from sympy.solvers.inequalities import solve_univariate_inequality

RELATIONAL_OPERATORS = {
    "gt": sympy.Gt,
    "lt": sympy.Lt,
    "ge": sympy.Ge,
    "le": sympy.Le,
}
X = symbols("x")


def _solve_equation(lhs: Any, rhs: Any) -> Dict[str, Any]:
    equation = lhs - rhs
    solutions = solveset(equation, X, domain=S.Reals)
    result = {"sol": solutions}

    _, denominator = equation.as_numer_denom()
    if denominator.free_symbols:
        result["dom"] = continuous_domain(equation, X, S.Reals)

    return result


def _solve_inequality(lhs: Any, rhs: Any, op: str) -> Dict[str, Any]:
    if op not in RELATIONAL_OPERATORS:
        return {"error": f"Unsupported inequality operator: {op}"}

    inequality = RELATIONAL_OPERATORS[op](lhs - rhs, 0)
    return {"sol": solve_univariate_inequality(inequality, X, domain=S.Reals)}


def _solve_expression(expr: Any, action: str, x_value: Any = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    if action == "simplify":
        result["res"] = simplify(expr)
    elif action == "expand":
        result["res"] = expand(expr)
    elif action == "factor":
        result["res"] = factor(expr)
    else:
        return {"error": f"Unsupported action: {action}"}

    if x_value is not None:
        try:
            result["evaluated"] = expr.subs(X, x_value).evalf()
        except Exception:
            result["evaluated_error"] = "Could not evaluate with given x_value"

    return {"sol": result}


def solve(expr_info):
    try:
        expression_type = expr_info.get("type")

        if expression_type == "equation":
            return _solve_equation(expr_info["lhs"], expr_info["rhs"])

        if expression_type == "inequality":
            return _solve_inequality(expr_info["lhs"], expr_info["rhs"], expr_info.get("op"))

        if expression_type == "expression":
            action = expr_info.get("action")
            if action is None:
                return {"error": "Action is required for expression type"}
            return _solve_expression(expr_info.get("value"), action, expr_info.get("x_value"))

        return {"error": "Unknown expression type"}
    except Exception as exc:
        return {"error": str(exc)}