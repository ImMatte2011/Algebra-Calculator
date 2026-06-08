from math_engine.engine import solve_expression


class CalculatorService:
    def solve(self, expr: str) -> str:
        return solve_expression(expr)
