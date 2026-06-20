# from ... import text    <- import dell'espressione dal file che riceve l'input da esp32
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

def parse_input(text, type_requested, action_requested=None, valore_x=None):
    try:
        text = text.replace(" ", "").strip().lower()

        # Disequazione
        if type_requested == "inequality":
            if not any(op in text for op in ops):
                return {"error": "Operatore di disequazione non trovato"}

            for op in sorted(ops, key=len, reverse=True):
                if op in text:
                    sx, dx = text.split(op, 1)

                    if sx.strip() == "" or dx.strip() =="":
                        return {"error": "Disequazione incompleta"}

                    sx = parse_expr(sx, transformations=trans)
                    dx = parse_expr(dx, transformations=trans)

                    op_name, _ = ops_map[op] # op_func non usata qui, ma potrebbe essere utile in futuro

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
                sx, dx = text, "0"  # Se non c'è '=', consideriamo l'equazione come se fosse "= 0"

            if sx.strip() == "" or dx.strip() == "":
                return {"error": "Equazione incompleta"}

            sx_parsed = parse_expr(sx, transformations=trans)
            dx_parsed = parse_expr(dx, transformations=trans)

            return {"type": "equation", "lhs": sx_parsed, "rhs": dx_parsed}

        elif type_requested == "expression":
            if "=" in text or any(op in text for op in ops):
                return {"error": "Un'espressione non deve contenere '=' o segni di disequazione"}
            
            parsed_expr = parse_expr(text, transformations=trans)
            return {
                "type": "expression",
                "value": parsed_expr,
                "action": action_requested,
                "valore_x": valore_x
            }

        else:
            return {"error": f"Type requested non valido: {type_requested}"}
            # Non dovrebbe capitare mai perché il telefono fa da bridge
            # e dovrebbe sempre inviare un type valido, 
            # ma è meglio gestire anche questo caso

    except Exception as e:
        return {"error": str(e)}