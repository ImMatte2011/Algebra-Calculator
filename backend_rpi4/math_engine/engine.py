from . import formatter, parser, solver


def solve_detailed(expr_str: str, type_requested: str, action_requested: str = None,
                   x_value=None, fmt: str = "plain", steps: bool = False) -> dict:
    """Run parsing, solving, and formatting; return either a result or an error."""
    if fmt not in formatter.FORMATS:
        return {"error": "Invalid format: {}".format(fmt)}

    parsed = parser.parse_input(
        expr_str,
        type_requested,
        action_requested,
        x_value=x_value,
    )
    if "error" in parsed:
        return {"error": parsed["error"]}
    parsed["steps"] = steps

    solved = solver.solve(parsed)
    if "error" in solved:
        return {"error": solved["error"]}
    try:
        output = formatter.format_solution(parsed["type"], solved.get("sol"), fmt)
    except Exception as exc:
        return {"error": "Formatting failed: {}".format(exc)}
    return {"result": output, "steps": solved.get("steps", [])}


def solve_expression(expr_str: str, type_requested: str, action_requested: str = None,
                     x_value=None) -> str:
    """Legacy string API: ``result:<text>`` or ``error:<text>``."""
    output = solve_detailed(
        expr_str,
        type_requested,
        action_requested,
        x_value=x_value,
    )
    if "error" in output:
        return "error:{}".format(output["error"])
    return "result:{}".format(output["result"])
