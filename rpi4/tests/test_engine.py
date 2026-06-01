from rpi4.math_engine.engine import solve_expression


def test_solve_expression_simple_polynomial():
    assert solve_expression("x^2") == "x**2"


def test_solve_expression_integral():
    result = solve_expression("integrate(x^2, x)")
    assert result in {"x**3/3", "x**3/3"}
