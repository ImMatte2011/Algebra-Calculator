import sympy
from rpi4.math_engine import parser, solver


def test_parse_expression():
    res = parser.parse_input("x^2")
    assert res["type"] == "expression"


def test_solve_equation():
    res = parser.parse_input("x^2-1=0")
    out = solver.risolvi(res)
    assert "sol" in out
    sols = set(out["sol"])
    assert sols == {sympy.Integer(-1), sympy.Integer(1)}


def test_solve_inequality():
    res = parser.parse_input("x>1")
    out = solver.risolvi(res)
    assert "sol" in out
    # simple sanity check: solution should reference 1
    assert "1" in str(out["sol"])


def test_expression_operations():
    res = parser.parse_input("2*x+2")
    out = solver.risolvi(res)
    assert "sol" in out
    sol = out["sol"]
    assert "simplified" in sol and "expanded" in sol and "factored" in sol
