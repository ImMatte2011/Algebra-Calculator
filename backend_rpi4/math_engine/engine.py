from __future__ import annotations

from typing import Any

from . import parser, solver


def _format_solution(solution: Any) -> str:
    if isinstance(solution, dict):
        output = str(solution.get("res", ""))
        if "evaluated" in solution:
            output = f"{output}={solution['evaluated']}"
        return output

    if solution is None:
        return ""

    return str(solution).replace("FiniteSet", "").replace("{", "").replace("}", "")


def solve_expression(expr_str: str, type_requested: str, action_requested: str = None, x_value=None) -> str:
    parsed = parser.parse_input(expr_str, type_requested, action_requested, x_value=x_value)
    if "error" in parsed:
        return f"error:{parsed['error']}"

    result = solver.solve(parsed)
    if "error" in result:
        return f"error:{result['error']}"

    output = _format_solution(result.get("sol"))
    return f"result:{output}"