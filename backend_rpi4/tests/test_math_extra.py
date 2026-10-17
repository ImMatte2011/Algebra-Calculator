import os
from pathlib import Path

import pytest

from backend_rpi4.math_engine.engine import solve_detailed
from backend_rpi4.math_engine.engine import solve_expression


@pytest.fixture(autouse=True)
def isolated_function_store(monkeypatch):
    store = Path(__file__).with_name(".test-functions-{}.json".format(os.getpid()))
    monkeypatch.setenv("FUNCTIONS_FILE", str(store))
    try:
        yield
    finally:
        try:
            store.unlink()
        except FileNotFoundError:
            pass


def result(expression, request_type, action=None, **options):
    output = solve_detailed(expression, request_type, action, **options)
    assert "error" not in output, output
    return output["result"]


def error(expression, request_type, action=None):
    output = solve_detailed(expression, request_type, action)
    assert "error" in output, output
    return output["error"]


def test_interval_formatting_and_formats():
    assert result("x>1", "inequality") == "(1,+oo)"
    assert result("x^2-1>0", "inequality") == "(-oo,-1) U (1,+oo)"
    assert result("x^2+1>0", "inequality") == "x in R"
    assert result("x^2+1<0", "inequality") == "no solution"
    assert result("x!=3", "inequality") == "(-oo,3) U (3,+oo)"
    assert result("x^2+1>0", "inequality", fmt="latex") == r"\forall x \in \mathbb{R}"
    assert result("x^2+1>0", "inequality", fmt="pretty") == "∀x ∈ ℝ"
    assert "x^{2}" in result("x^2", "expression", "simplify", fmt="latex")
    assert "Invalid format" in solve_detailed(
        "x", "expression", "simplify", fmt="unknown"
    )["error"]


def test_systems():
    assert result("x>1;x<5", "ineq_system") == "(1,5)"
    assert result("x>1;x<0", "ineq_system") == "no solution"
    assert result("x^2>4;x<10", "ineq_system") == "(-oo,-2) U (2,10)"
    assert result("x+y=3;x-y=1", "lin_system") == "x=2, y=1"
    assert result("x+y=3;x+y=4", "lin_system") == "no solution"
    assert "free" in result("x+y=3;2x+2y=6", "lin_system")
    assert "not linear" in error("x^2+y=3;x-y=1", "lin_system")
    assert "Only x and y" in error("x+z=3;x-z=1", "lin_system")
    assert error("x+y=3", "lin_system")
    assert error("1<x<5", "inequality")


def test_number_actions():
    assert result("360", "number", "primes") == "2^3*3^2*5"
    assert result("17", "number", "primes") == "17 is prime"
    assert result("12,18,30", "number", "gcd") == "6"
    assert result("12;18", "number", "gcd") == "6"
    assert result("4,6", "number", "lcm") == "12"
    assert error("1", "number", "primes")
    assert error("1.5", "number", "gcd")
    assert error("100000000000000000000", "number", "primes")


def test_matrix_actions():
    assert result("1,2;3,4", "matrix", "det") == "-2"
    assert result("1,2;3,4", "matrix", "inv") == "-2,1;3/2,-1/2"
    assert result("1,2;3,4", "matrix", "trans") == "1,3;2,4"
    assert result("1,2,3;4,5,6;7,8,10", "matrix", "det") == "-3"
    assert result("x,1;1,x", "matrix", "det") == "x**2 - 1"
    assert "singular" in error("1,2;2,4", "matrix", "inv")
    assert "square" in error("1,2,3;4,5,6", "matrix", "det")
    assert "same length" in error("1,2;3", "matrix", "det")


def test_custom_function_store_and_expansion():
    assert result("f(x)=x^2+1", "function", "define") == "f(x)=x**2 + 1 saved"
    assert result("f(3)", "expression", "simplify") == "10"
    assert result("f(x)=5", "equation") == "-2, 2"
    assert result("g(x,y)=f(x)+y", "function", "define").startswith(
        "g(x,y)=x**2 + y + 1"
    )
    assert result("g(2,3)", "expression", "simplify") == "8"
    assert "f(x)" in result("list", "function", "list")
    assert result("f", "function", "delete") == "f deleted"
    assert error("f", "function", "delete")
    result("f(x)=x+1", "function", "define")
    result("f(x)=f(x)*2", "function", "define")
    assert result("f(1)", "expression", "simplify") == "4"
    assert error("f(x)=x+y", "function", "define")
    assert error("f(z)=z", "function", "define")
    assert error("f(x,x)=x", "function", "define")


def test_steps_and_legacy_api():
    assert solve_detailed("x^2-1=0", "equation")["steps"] == []
    steps = solve_detailed("x^2-1=0", "equation", steps=True)["steps"]
    assert steps and steps[-1].startswith("Solutions:")
    signs = solve_detailed("(x-1)/(x+2)>=0", "inequality", steps=True)["steps"]
    assert any(step.startswith("Signs:") for step in signs)
    assert solve_expression("x^2", "expression", "simplify") == "result:x**2"
    assert solve_expression("x=", "equation").startswith("error:")


def test_parser_rejects_unsupported_characters_and_long_inputs():
    assert "Invalid character" in error("__import__('os')", "expression", "simplify")
    assert "too long" in error("x" * 121, "expression", "simplify")


def test_trigonometric_hyperbolic_and_logarithmic_expressions():
    assert result("sin(0)+cos(0)", "expression", "simplify") == "1"
    assert result("sinh(0)+log(e)", "expression", "simplify") == "1"
