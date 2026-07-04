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
    ">":  "gt",
    "<":  "lt",
    ">=": "ge",
    "<=": "le",
}

def parse_input(text, type_requested, action_requested=None, x_value=None):
    try:
        text = text.replace(" ", "").strip().lower()

        # Inequality
        if type_requested == "inequality":
            if not any(op in text for op in ops):
                return {"error": "Inequality operator not found"}

            for op in sorted(ops, key=len, reverse=True):
                if op in text:
                    sx, dx = text.split(op, 1)

                    if sx.strip() == "" or dx.strip() == "":
                        return {"error": "Incomplete inequality"}

                    sx = parse_expr(sx, transformations=trans)
                    dx = parse_expr(dx, transformations=trans)

                    op_name = ops_map[op]

                    return {
                        "type": "inequality",
                        "lhs": sx,
                        "rhs": dx,
                        "op": op_name
                    }

        elif type_requested == "equation":
            if "=" in text:
                sx, dx = text.split("=", 1)
            else:
                sx, dx = text, "0"  # If there is no '=', treat it as an equation equal to 0

            if sx.strip() == "" or dx.strip() == "":
                return {"error": "Incomplete equation"}

            sx_parsed = parse_expr(sx, transformations=trans)
            dx_parsed = parse_expr(dx, transformations=trans)

            return {"type": "equation", "lhs": sx_parsed, "rhs": dx_parsed}

        elif type_requested == "expression":
            if "=" in text or any(op in text for op in ops):
                return {"error": "An expression must not contain '=' or inequality signs"}
            
            parsed_expr = parse_expr(text, transformations=trans)
            return {
                "type": "expression",
                "value": parsed_expr,
                "action": action_requested,
                "x_value": x_value
            }

        else:
            return {"error": f"Invalid type requested: {type_requested}"}
            # This should never happen because the phone bridge is expected
            # to always send a valid type, but we handle it defensively.

    except Exception as e:
        return {"error": str(e)}