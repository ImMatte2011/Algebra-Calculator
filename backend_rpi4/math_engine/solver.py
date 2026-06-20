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

            if expr_info.get("valore_x") is not None:
                try:
                    val = expr_info["valore_x"]
                    result["evaluated"] = expr.subs(x, val).evalf()
                except Exception:
                    result["evaluated_error"] = "Could not evaluate with given valore_x"
            return {"sol": result}

        elif t == "expression" and expr_info.get("action") is None:
            return {"error": "Action is required for expression type"}
            # Non dovrebbe capitare mai perché il telefono fa da bridge
            # e dovrebbe sempre inviare un action se "type"=="expression", 
            # ma è meglio gestire anche questo caso se il programma su ESP32
            # dovesse avere un bug o il telefono stesso dovesse inviare un messaggio malformato

        return {"error": "Unknown expression type"}
    except Exception as e:
        return {"error": str(e)}