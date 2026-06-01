import sympy
from sympy import symbols, S, solveset, simplify, expand, factor
from sympy.calculus.util import continuous_domain
from sympy.solvers.inequalities import solve_univariate_inequality
# Use SymPy relational classes via the sympy namespace
ops = {"gt": sympy.Gt, "lt": sympy.Lt, "ge": sympy.Ge, "le": sympy.Le}
x = symbols("x")


def risolvi(expr_info):
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

        if t == "inequality":
            op = expr_info.get("op")
            if op not in ops:
                return {"error": f"Unsupported inequality operator: {op}"}
            ineq = ops[op](expr_info["lhs"] - expr_info["rhs"], 0)
            sol = solve_univariate_inequality(ineq, x, domain=S.Reals)
            return {"sol": sol}

        if t == "expression":
            expr = expr_info.get("value")
            result = {
                "simplified": simplify(expr),
                "expanded": expand(expr),
                "factored": factor(expr),
            }
            if "valore_x" in expr_info:
                try:
                    val = expr_info["valore_x"]
                    result["evaluated"] = expr.subs(x, val).evalf()
                except Exception:
                    result["evaluated_error"] = "Could not evaluate with given valore_x"
            return {"sol": result}

        return {"error": "Unknown expression type"}
    except Exception as e:
        return {"error": str(e)}