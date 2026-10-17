"""Persistent store for user-defined functions."""

import json
import os
import threading
from pathlib import Path

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

_LOCK = threading.Lock()
_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def _path():
    return Path(os.getenv("FUNCTIONS_FILE", "data/functions.json"))


def _load():
    path = _path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ValueError("Could not read function store: {}".format(exc)) from exc
    if not isinstance(data, dict):
        raise ValueError("Function store must contain a JSON object")
    for name, definition in data.items():
        if (not isinstance(name, str) or len(name) != 1 or not name.isalpha()
                or not isinstance(definition, dict)
                or not isinstance(definition.get("params"), list)
                or not isinstance(definition.get("body"), str)):
            raise ValueError("Invalid function definition in store")
    return data


def _write(data):
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        raise ValueError("Could not write function store: {}".format(exc)) from exc


def save(name, params, body):
    with _LOCK:
        data = _load()
        data[name] = {"params": list(params), "body": str(body)}
        _write(data)


def delete(name):
    """Delete a function and return whether it existed."""
    with _LOCK:
        data = _load()
        if name not in data:
            return False
        del data[name]
        _write(data)
        return True


def list_all():
    """Return ``{name: (params, body_string)}``, sorted by name."""
    with _LOCK:
        data = _load()
    return {
        name: (definition["params"], definition["body"])
        for name, definition in sorted(data.items())
    }


def lambdas():
    """Build fresh SymPy lambdas for use as ``parse_expr`` local names."""
    output = {}
    for name, (params, body) in list_all().items():
        local_dict = {
            "x": sympy.Symbol("x"),
            "y": sympy.Symbol("y"),
            "pi": sympy.pi,
            "E": sympy.E,
        }
        expression = parse_expr(
            body,
            transformations=_TRANSFORMATIONS,
            local_dict=local_dict,
        )
        output[name] = sympy.Lambda(tuple(sympy.Symbol(p) for p in params), expression)
    return output
