from __future__ import annotations

from typing import Any

from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

OPERATORS = (">=", "<=", ">", "<")
OPS_MAP = {
    ">": "gt",
    "<": "lt",
    ">=": "ge",
    "<=": "le",
}


def _normalize_text(text: Any) -> str:
    if text is None:
        raise ValueError("Input cannot be empty")

    normalized = str(text).replace(" ", "").strip().lower()
    if not normalized:
        raise ValueError("Input cannot be empty")

    return normalized


def _parse_side(raw_text: str):
    return parse_expr(raw_text, transformations=TRANSFORMATIONS)


def _parse_inequality(text: str):
    for op in sorted(OPERATORS, key=len, reverse=True):
        if op not in text:
            continue

        left_side, right_side = text.split(op, 1)
        if not left_side or not right_side:
            return {"error": "Incomplete inequality"}

        return {
            "type": "inequality",
            "lhs": _parse_side(left_side),
            "rhs": _parse_side(right_side),
            "op": OPS_MAP[op],
        }

    return {"error": "Inequality operator not found"}


def parse_input(text, type_requested, action_requested=None, x_value=None):
    try:
        normalized_text = _normalize_text(text)

        if type_requested == "inequality":
            if not any(op in normalized_text for op in OPERATORS):
                return {"error": "Inequality operator not found"}
            return _parse_inequality(normalized_text)

        if type_requested == "equation":
            if "=" in normalized_text:
                left_side, right_side = normalized_text.split("=", 1)
            else:
                left_side, right_side = normalized_text, "0"

            if not left_side or not right_side:
                return {"error": "Incomplete equation"}

            return {
                "type": "equation",
                "lhs": _parse_side(left_side),
                "rhs": _parse_side(right_side),
            }

        if type_requested == "expression":
            if "=" in normalized_text or any(op in normalized_text for op in OPERATORS):
                return {"error": "An expression must not contain '=' or inequality signs"}

            return {
                "type": "expression",
                "value": _parse_side(normalized_text),
                "action": action_requested,
                "x_value": x_value,
            }

        return {"error": f"Invalid type requested: {type_requested}"}
    except Exception as exc:
        return {"error": str(exc)}