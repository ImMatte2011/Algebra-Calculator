import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sympy
from math_engine import parser, solver
from math_engine.engine import solve_expression


class TestParser:
    """Test the parser module for input parsing"""

    def test_parse_simple_expression(self):
        res = parser.parse_input("x^2", "expression")
        assert res["type"] == "expression"
        assert "value" in res

    def test_parse_equation(self):
        res = parser.parse_input("x^2-1=0", "equation")
        assert res["type"] == "equation"
        assert "lhs" in res and "rhs" in res

    def test_parse_inequality_gt(self):
        res = parser.parse_input("x>1", "inequality")
        assert res["type"] == "inequality"
        assert res["op"] == "gt"

    def test_parse_inequality_lt(self):
        res = parser.parse_input("x<5", "inequality")
        assert res["type"] == "inequality"
        assert res["op"] == "lt"

    def test_parse_inequality_ge(self):
        res = parser.parse_input("x>=0", "inequality")
        assert res["type"] == "inequality"
        assert res["op"] == "ge"

    def test_parse_inequality_le(self):
        res = parser.parse_input("x<=10", "inequality")
        assert res["type"] == "inequality"
        assert res["op"] == "le"

    def test_parse_incomplete_equation(self):
        res = parser.parse_input("x=", "equation")
        assert "error" in res

    def test_parse_incomplete_inequality(self):
        res = parser.parse_input("x>", "inequality")
        assert "error" in res

    def test_parse_with_multiple_variables(self):
        res = parser.parse_input("x^2 + y^2", "expression")
        assert res["type"] == "expression"

    def test_parse_with_implicit_multiplication(self):
        res = parser.parse_input("2x+3", "expression")
        assert res["type"] == "expression"
        assert "value" in res


class TestSolver:
    """Test the solver module for equation/inequality resolution"""

    def test_solve_simple_quadratic(self):
        res = parser.parse_input("x^2-1=0", "equation")
        out = solver.solve(res)
        assert "sol" in out
        sols = set(out["sol"])
        assert sols == {sympy.Integer(-1), sympy.Integer(1)}

    def test_solve_linear_equation(self):
        res = parser.parse_input("2*x+3=7", "equation")
        out = solver.solve(res)
        assert "sol" in out
        sols = set(out["sol"])
        assert sympy.Integer(2) in sols

    def test_solve_inequality_gt(self):
        res = parser.parse_input("x>1", "inequality")
        out = solver.solve(res)
        assert "sol" in out
        assert "1" in str(out["sol"])

    def test_solve_inequality_lt(self):
        res = parser.parse_input("x<5", "inequality")
        out = solver.solve(res)
        assert "sol" in out
        assert "5" in str(out["sol"])

    def test_solve_cubic_equation(self):
        res = parser.parse_input("x^3-8=0", "equation")
        out = solver.solve(res)
        assert "sol" in out
        assert sympy.Integer(2) in out["sol"]

    def test_expression_simplification(self):
        res = parser.parse_input("2*x+2", "expression", "simplify")
        out = solver.solve(res)
        assert "sol" in out
        sol = out["sol"]
        assert "res" in sol

    def test_expression_factoring(self):
        res = parser.parse_input("x^2-1", "expression", "factor")
        out = solver.solve(res)
        assert "sol" in out
        sol = out["sol"]
        assert "res" in sol
        assert "(x - 1)*(x + 1)" in str(sol["res"])

    def test_no_solution_equation(self):
        res = parser.parse_input("x^2+1=0", "equation")
        out = solver.solve(res)
        assert "sol" in out
        assert len(out["sol"]) == 0


class TestEngine:
    """Test the main engine wrapper"""

    def test_engine_simple_polynomial(self):
        result = solve_expression("x^2", "expression", "simplify")
        assert "x**2" in result

    def test_engine_equation(self):
        result = solve_expression("x^2-1=0", "equation")
        assert "-1" in result or "1" in result

    def test_engine_linear_equation(self):
        result = solve_expression("2*x+3=7", "equation")
        assert "2" in result

    def test_engine_inequality(self):
        result = solve_expression("x>1", "inequality")
        assert "error" not in result.lower()
        assert "1" in result

    def test_engine_invalid_input(self):
        result = solve_expression("x=", "equation")
        assert "error" in result.lower()

    def test_engine_expression_simplification(self):
        result = solve_expression("2*x+2*x", "expression", "simplify")
        assert "4*x" in result or "4x" in result.replace(" ", "")

    def test_engine_fractional_expression(self):
        result = solve_expression("(x+1)/(x-1)", "expression", "simplify")
        assert "error" not in result.lower()

    def test_engine_complex_polynomial(self):
        result = solve_expression("(x-2)*(x-3)=0", "equation")
        assert "2" in result and "3" in result

    def test_engine_multiple_variable_expression(self):
        result = solve_expression("x^2 + y^2", "expression", "simplify")
        assert "error" not in result.lower()


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_equation_side(self):
        res = parser.parse_input("=x", "equation")
        assert "error" in res

    def test_very_large_coefficient(self):
        result = solve_expression("1000000*x=5000000", "equation")
        assert "error" not in result.lower()

    def test_nested_parentheses(self):
        result = solve_expression("((x+1)+(x+2))=10", "equation")
        assert "error" not in result.lower()

    def test_xor_operator_conversion(self):
        res = parser.parse_input("x^3", "expression")
        assert res["type"] == "expression"
        assert "value" in res
