import sympy
from sympy import symbols, S, solveset, simplify, expand, factor
from sympy.calculus.util import continuous_domain
from sympy.solvers.inequalities import solve_univariate_inequality
# Use SymPy relational classes via the sympy namespace
ops = {"gt": sympy.Gt, "lt": sympy.Lt, "ge": sympy.Ge, "le": sympy.Le}
x = symbols("x")


def solve(expr_info):
    try:
        t = expr_info.get("type")

        if t == "equation":
            eq_expr = expr_info["lhs"] - expr_info["rhs"]
            sol = solveset(eq_expr, x, domain=S.Reals)
            num, den = eq_expr.as_numer_denom()
            result = {"sol": sol}
            if den.free_symbols:
                result["dom"] = continuous_domain(eq_expr, x, S.Reals)
            return result

        elif t == "inequality":
            op = expr_info.get("op")
            if op not in ops:
                return {"error": f"Unsupported inequality operator: {op}"}
            ineq = ops[op](expr_info["lhs"] - expr_info["rhs"], 0)
            sol = solve_univariate_inequality(ineq, x, domain=S.Reals)
            return {"sol": sol}

        elif t == "expression" and expr_info.get("action") is not None:
            expr = expr_info.get("value")
            act = expr_info.get("action")
            result = {}

            if act == "simplify":
                result["res"] = simplify(expr)
            elif act == "expand":
                result["res"] = expand(expr)
            elif act == "factor":
                result["res"] = factor(expr)
            else:
                return {"error": f"Unsupported action: {act}"}

            if expr_info.get("x_value") is not None:
                try:
                    val = expr_info["x_value"]
                    result["evaluated"] = expr.subs(x, val).evalf()
                except Exception:
                    result["evaluated_error"] = "Could not evaluate with given x_value"
            return {"sol": result}

        elif t == "expression" and expr_info.get("action") is None:
            return {"error": "Action is required for expression type"}
            # This should never happen because the phone bridge is expected
            # to always send an action when "type" == "expression",
            # but we handle it defensively in case the ESP32 firmware or the phone
            # sends malformed data.

        return {"error": "Unknown expression type"}
    except Exception as e:
        return {"error": str(e)}