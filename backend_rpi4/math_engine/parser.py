import re

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from . import functions

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)
MAX_LEN = 120
MAX_SYSTEM = 4
MAX_MATRIX = 5
MAX_INT_DIGITS = 15
_ALLOWED = re.compile(r"^[a-z0-9+\-*/^().,;=<>!]*$")
_COMPARISON = re.compile(r"!=|>=|<=|>|<")
_OPS_MAP = {">": "gt", "<": "lt", ">=": "ge", "<=": "le", "!=": "ne"}


def _parse(text):
    if not text:
        raise ValueError("Expression cannot be empty")
    local_dict = {
        "x": sympy.Symbol("x"),
        "y": sympy.Symbol("y"),
        "pi": sympy.pi,
        "e": sympy.E,
        "oo": sympy.oo,
        "inf": sympy.oo,
        "sqrt": sympy.sqrt,
        "abs": sympy.Abs,
        "ln": sympy.log,
    }
    local_dict.update(functions.lambdas())
    return parse_expr(
        text,
        transformations=TRANSFORMATIONS,
        local_dict=local_dict,
    )


def _parse_inequality(text):
    operators = _COMPARISON.findall(text)
    if not operators:
        return {"error": "Inequality operator not found"}
    if len(operators) != 1:
        return {"error": "One comparison per inequality (use ';' for systems)"}
    operator = operators[0]
    left, right = text.split(operator, 1)
    if not left or not right:
        return {"error": "Incomplete inequality"}
    return {
        "type": "inequality",
        "lhs": _parse(left),
        "rhs": _parse(right),
        "op": _OPS_MAP[operator],
    }


def _split_system(text):
    parts = text.split(";")
    if not 2 <= len(parts) <= MAX_SYSTEM or any(not part for part in parts):
        return None, "A system needs 2-{} items separated by ';'".format(MAX_SYSTEM)
    return parts, None


def _parse_function(text, action):
    if action == "list":
        return {"type": "function", "action": "list"}
    if action == "delete":
        if not re.fullmatch(r"[a-z]", text):
            return {"error": "Give the function name, e.g. f"}
        return {"type": "function", "action": "delete", "name": text}
    if action != "define":
        return {"error": "Invalid function action: {}".format(action)}

    match = re.fullmatch(r"([a-z])\(([xy](?:,[xy])*)\)=(.+)", text)
    if not match:
        return {"error": "Use the form f(x)=expression"}
    name, params, body_text = match.group(1), match.group(2).split(","), match.group(3)
    if name in ("x", "y"):
        return {"error": "Name 'x'/'y' is reserved"}
    if len(set(params)) != len(params):
        return {"error": "Duplicate parameter"}
    body = _parse(body_text)
    extra = body.free_symbols - {sympy.Symbol(param) for param in params}
    if extra:
        return {"error": "Undefined variable: " + ", ".join(sorted(map(str, extra)))}
    return {
        "type": "function",
        "action": "define",
        "name": name,
        "params": params,
        "body": body,
    }


def parse_input(text, type_requested, action_requested=None, x_value=None):
    try:
        if text is None:
            return {"error": "Input cannot be empty"}
        normalized = str(text).replace(" ", "").strip().lower()
        if not normalized:
            return {"error": "Input cannot be empty"}
        if len(normalized) > MAX_LEN:
            return {"error": "Input too long (max {} characters)".format(MAX_LEN)}
        if not _ALLOWED.fullmatch(normalized):
            return {"error": "Invalid character in input"}

        if type_requested == "inequality":
            return _parse_inequality(normalized)

        if type_requested == "equation":
            if normalized.count("=") > 1 or _COMPARISON.search(normalized):
                return {"error": "An equation must contain at most one '=' and no inequalities"}
            left, right = normalized.split("=", 1) if "=" in normalized else (normalized, "0")
            if not left or not right:
                return {"error": "Incomplete equation"}
            return {"type": "equation", "lhs": _parse(left), "rhs": _parse(right)}

        if type_requested == "expression":
            if "=" in normalized or _COMPARISON.search(normalized):
                return {"error": "An expression must not contain '=' or inequality signs"}
            return {
                "type": "expression",
                "value": _parse(normalized),
                "action": action_requested,
                "x_value": x_value,
            }

        if type_requested == "ineq_system":
            parts, error = _split_system(normalized)
            if error:
                return {"error": error}
            items = []
            for part in parts:
                item = _parse_inequality(part)
                if "error" in item:
                    return item
                items.append(item)
            return {"type": "ineq_system", "items": items}

        if type_requested == "lin_system":
            parts, error = _split_system(normalized)
            if error:
                return {"error": error}
            equations = []
            for part in parts:
                if part.count("=") != 1 or _COMPARISON.search(part):
                    return {"error": "Each equation needs exactly one '='"}
                left, right = part.split("=")
                if not left or not right:
                    return {"error": "Incomplete equation"}
                equations.append((_parse(left), _parse(right)))
            return {"type": "lin_system", "eqs": equations}

        if type_requested == "number":
            values = normalized.split(",") if "," in normalized else normalized.split(";")
            if (not 1 <= len(values) <= 6
                    or any(not re.fullmatch(r"\d{1,%d}" % MAX_INT_DIGITS, value)
                           for value in values)):
                return {"error": "Enter 1-6 integers with at most {} digits".format(MAX_INT_DIGITS)}
            return {
                "type": "number",
                "action": action_requested,
                "values": [int(value) for value in values],
            }

        if type_requested == "matrix":
            rows = normalized.split(";")
            cells = [row.split(",") for row in rows]
            if any(not cell for row in cells for cell in row):
                return {"error": "Empty matrix element"}
            if len({len(row) for row in cells}) != 1:
                return {"error": "All rows must have the same length"}
            if len(cells) > MAX_MATRIX or len(cells[0]) > MAX_MATRIX:
                return {"error": "Matrix too big (max {}x{})".format(MAX_MATRIX, MAX_MATRIX)}
            return {
                "type": "matrix",
                "action": action_requested,
                "value": sympy.Matrix([[_parse(cell) for cell in row] for row in cells]),
            }

        if type_requested == "function":
            return _parse_function(normalized, action_requested)

        return {"error": "Invalid type requested: {}".format(type_requested)}
    except Exception as exc:
        return {"error": str(exc)}
