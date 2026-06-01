# from ... import testo    <- import dell'esressione dal file che riceve l'input da esp32
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)

trans = standard_transformations + (
    implicit_multiplication_application,
    convert_xor
)
ops = [">=", "<=", ">", "<"]
ops_map = {
    ">": ("gt", lambda a, b: a > b),
    "<": ("lt", lambda a, b: a < b),
    ">=": ("ge", lambda a, b: a >= b),
    "<=": ("le", lambda a, b: a <= b),
}

def parse_input(testo):
    try:

        if any(op in testo for op in ops):
            for op in sorted(ops, key=len, reverse=True):
                if op in testo:
                    sx, dx = testo.split(op, 1)

                    if sx.strip() == "" or dx.strip() == "":
                        return {"error": "Disequazione incompleta"}

                    sx = parse_expr(sx, transformations=trans)
                    dx = parse_expr(dx, transformations=trans)

                    op_name, op_func = ops_map[op]

                    return {
                        "type": "inequality",
                        "lhs": sx,
                        "rhs": dx,
                        "op": op_name
                    }

        elif "=" in testo:
            sx, dx = testo.split("=", 1)

            if sx.strip() == "" or dx.strip() == "":
                return {"error": "Equazione incompleta"}

            sx = parse_expr(sx, transformations=trans)
            dx = parse_expr(dx, transformations=trans)

            return {"type": "equation", "lhs": sx, "rhs": dx}

        else:
            parsed_expr = parse_expr(testo, transformations=trans)
            return {"type": "expression", "value": parsed_expr}

    except Exception as e:
        return {"error": str(e)}