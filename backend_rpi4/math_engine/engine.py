from math_engine import parser, solver

def solve_expression(expr_str: str, type_requested: str, action_requested: str = None, x_value=None) -> str:
    # 1. Call the parser
    parsed = parser.parse_input(expr_str, type_requested, action_requested, x_value=x_value)
    if "error" in parsed:
        return f"error:{parsed['error']}"

    # 2. Pass the parsed dictionary to the solver
    result = solver.solve(parsed)
    if "error" in result:
        return f"error:{result['error']}"

    # 3. Extract the "sol" field and normalize the output for the ESP32 display
    solution = result.get("sol")
    
    if isinstance(solution, dict):
        # Caso tipo "expression" (ha le chiavi "res" ed eventualmente "evaluated")
        output = str(solution.get("res", ""))
        if "evaluated" in solution:
            output += f"={solution['evaluated']}"
    else:
        # Equation/inequality result (SymPy returns Sets like FiniteSet(2) or {2})
        # Strip wrapper text and braces for cleaner LCD output.
        output = str(solution).replace("FiniteSet", "").replace("{", "").replace("}", "")

    return f"result:{output}"