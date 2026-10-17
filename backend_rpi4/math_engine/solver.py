import math
from functools import reduce

import sympy
from sympy import S, expand, factor, simplify, solveset, symbols, together
from sympy.calculus.util import continuous_domain
from sympy.solvers.inequalities import solve_univariate_inequality

from . import formatter, functions

_OPERATORS = {"gt": sympy.Gt, "lt": sympy.Lt, "ge": sympy.Ge, "le": sympy.Le}
_OP_SYMBOLS = {"gt": ">", "lt": "<", "ge": ">=", "le": "<=", "ne": "!="}
x, y = symbols("x y")


def _plain(request_type, solution):
    return formatter.format_solution(request_type, solution, formatter.PLAIN)


def _inequality_set(lhs, rhs, operator):
    difference = lhs - rhs
    if operator == "ne":
        return S.Reals - solveset(difference, x, domain=S.Reals)
    if operator not in _OPERATORS:
        raise ValueError("Unsupported inequality operator: {}".format(operator))
    return solve_univariate_inequality(
        _OPERATORS[operator](difference, 0),
        x,
        domain=S.Reals,
        relational=False,
    )


def _equation_steps(lhs, rhs, solution):
    difference = together(lhs - rhs)
    numerator, denominator = difference.as_numer_denom()
    steps = ["Move all terms to the left: {} = 0".format(lhs - rhs)]
    if denominator.free_symbols:
        steps.append(
            "Rational equation: solve {} = 0 with {} != 0".format(
                factor(numerator), factor(denominator)
            )
        )
    else:
        factored = factor(numerator)
        if factored.is_Mul and sum(1 for item in factored.args if item.has(x)) > 1:
            steps.extend([
                "Factor: {} = 0".format(factored),
                "Zero product rule: set each factor to 0",
            ])
    steps.append("Solutions: " + _plain("equation", solution))
    return steps


def _inequality_steps(lhs, rhs, operator, solution):
    difference = factor(together(lhs - rhs))
    steps = [
        "Study the sign of f(x) = {} ({} 0)".format(
            difference, _OP_SYMBOLS[operator]
        )
    ]
    numerator, denominator = difference.as_numer_denom()
    zeros = solveset(numerator, x, domain=S.Reals)
    poles = solveset(denominator, x, domain=S.Reals) if denominator.has(x) else S.EmptySet
    if isinstance(zeros, sympy.FiniteSet) and zeros:
        steps.append("Zeros: " + ", ".join(map(str, zeros)))
    if isinstance(poles, sympy.FiniteSet) and poles:
        steps.append("Excluded (denominator = 0): " + ", ".join(map(str, poles)))
    if isinstance(zeros, sympy.FiniteSet) and isinstance(poles, sympy.FiniteSet):
        points = sorted(set(zeros) | set(poles), key=lambda value: float(value))
        if points:
            samples = (
                [points[0] - 1]
                + [(left + right) / 2 for left, right in zip(points, points[1:])]
                + [points[-1] + 1]
            )
            labels = (
                ["x<{}".format(points[0])]
                + ["{}<x<{}".format(left, right) for left, right in zip(points, points[1:])]
                + ["x>{}".format(points[-1])]
            )
            signs = []
            for sample in samples:
                sign = difference.subs(x, sample).is_positive
                signs.append("+" if sign is True else "-" if sign is False else "?")
            steps.append(
                "Signs: " + "; ".join(
                    "{} {}".format(label, sign) for label, sign in zip(labels, signs)
                )
            )
    steps.append("Solution: " + _plain("inequality", solution))
    return steps


def _inequality_system_steps(items, item_sets, solution):
    steps = [
        "({}) {} {} {} -> {}".format(
            index, item["lhs"], _OP_SYMBOLS[item["op"]], item["rhs"],
            _plain("inequality", item_set),
        )
        for index, (item, item_set) in enumerate(zip(items, item_sets), 1)
    ]
    steps.append("Intersection: " + _plain("ineq_system", solution))
    return steps


def _linear_system_steps(equations, solution):
    matrix, constants = sympy.linear_eq_to_matrix(equations, [x, y])
    steps = [
        "Matrix form: A=[{}], b=[{}]".format(
            formatter.matrix_plain(matrix), formatter.matrix_plain(constants)
        )
    ]
    if matrix.shape == (2, 2):
        determinant = matrix.det()
        if determinant != 0:
            dx_matrix, dy_matrix = matrix.copy(), matrix.copy()
            dx_matrix[:, 0] = constants
            dy_matrix[:, 1] = constants
            dx, dy = dx_matrix.det(), dy_matrix.det()
            steps.extend([
                "Cramer: D={}, Dx={}, Dy={}".format(determinant, dx, dy),
                "x = Dx/D = {}, y = Dy/D = {}".format(dx / determinant, dy / determinant),
            ])
        else:
            steps.append("D = 0: no unique solution")
    else:
        reduced, _ = matrix.row_join(constants).rref()
        steps.append(
            "Row reduction of [A|b]: [{}]".format(formatter.matrix_plain(reduced))
        )
    steps.append("Solution: " + _plain("lin_system", solution))
    return steps


def _euclidean_gcd(left, right):
    if left < right:
        left, right = right, left
    lines = []
    while right:
        quotient, remainder = divmod(left, right)
        lines.append("{} = {}*{} + {}".format(left, quotient, right, remainder))
        left, right = right, remainder
    return left, lines


def _gcd_lcm_steps(values, action):
    steps = []
    accumulator = values[0]
    for value in values[1:]:
        gcd, divisions = _euclidean_gcd(accumulator, value)
        steps.extend(divisions)
        steps.append("gcd({}, {}) = {}".format(accumulator, value, gcd))
        if action == "lcm":
            result = abs(accumulator * value) // gcd if gcd else 0
            steps.append("lcm({}, {}) = {}".format(accumulator, value, result))
            accumulator = result
        else:
            accumulator = gcd
    return steps


def _prime_steps(number, factors):
    steps = []
    remaining = number
    for prime, exponent in sorted(factors.items()):
        for _ in range(exponent):
            steps.append("{} / {} = {}".format(remaining, prime, remaining // prime))
            remaining //= prime
    return steps[:40]


def _determinant_steps(matrix, determinant):
    if matrix.rows == 1:
        return ["det = {}".format(determinant)]
    if matrix.rows == 2:
        a, b, c, d = matrix[0, 0], matrix[0, 1], matrix[1, 0], matrix[1, 1]
        return [
            "det = a*d - b*c = ({})*({}) - ({})*({})".format(a, d, b, c),
            "det = {}".format(determinant),
        ]
    if matrix.rows == 3:
        terms = [
            "{} ({})*({})".format(
                "+" if col % 2 == 0 else "-",
                matrix[0, col],
                matrix.minor_submatrix(0, col).det(),
            )
            for col in range(3)
        ]
        return [
            "Expand along row 1: det = " + " ".join(terms).lstrip("+ "),
            "det = {}".format(determinant),
        ]
    return ["{}x{} matrix: cofactor expansion".format(matrix.rows, matrix.cols),
            "det = {}".format(determinant)]


def solve(expr_info):
    try:
        request_type = expr_info.get("type")
        want_steps = bool(expr_info.get("steps"))

        if request_type == "equation":
            difference = expr_info["lhs"] - expr_info["rhs"]
            numerator, denominator = difference.as_numer_denom()
            solution = solveset(numerator, x, domain=S.Reals)
            if denominator.has(x):
                domain = continuous_domain(difference, x, S.Reals)
                solution = solution.intersect(domain)
            result = {"sol": solution}
            if want_steps:
                result["steps"] = _equation_steps(
                    expr_info["lhs"], expr_info["rhs"], solution
                )
            return result

        if request_type == "inequality":
            operator = expr_info.get("op")
            solution = _inequality_set(expr_info["lhs"], expr_info["rhs"], operator)
            result = {"sol": solution}
            if want_steps:
                result["steps"] = _inequality_steps(
                    expr_info["lhs"], expr_info["rhs"], operator, solution
                )
            return result

        if request_type == "ineq_system":
            items = expr_info["items"]
            item_sets = [
                _inequality_set(item["lhs"], item["rhs"], item["op"])
                for item in items
            ]
            solution = sympy.Intersection(*item_sets)
            result = {"sol": solution}
            if want_steps:
                result["steps"] = _inequality_system_steps(items, item_sets, solution)
            return result

        if request_type == "lin_system":
            equations = [lhs - rhs for lhs, rhs in expr_info["eqs"]]
            used_symbols = set().union(*(equation.free_symbols for equation in equations))
            if not used_symbols <= {x, y}:
                return {"error": "Only x and y are allowed in linear systems"}
            for equation in equations:
                try:
                    is_linear = sympy.Poly(equation, x, y).total_degree() <= 1
                except sympy.PolynomialError:
                    is_linear = False
                if not is_linear:
                    return {"error": "The system is not linear"}
            solution = sympy.linsolve(equations, [x, y])
            result = {"sol": solution}
            if want_steps:
                result["steps"] = _linear_system_steps(equations, solution)
            return result

        if request_type == "number":
            action, values = expr_info.get("action"), expr_info["values"]
            if action == "primes":
                if len(values) != 1 or values[0] < 2:
                    return {"error": "Enter one integer >= 2"}
                factors = sympy.factorint(values[0])
                result = {"sol": {"factors": factors, "n": values[0]}}
                if want_steps:
                    result["steps"] = _prime_steps(values[0], factors)
                return result
            if action in ("gcd", "lcm"):
                if not 2 <= len(values) <= 6:
                    return {"error": "Enter 2-6 integers separated by ','"}
                operation = math.gcd if action == "gcd" else math.lcm
                result_value = reduce(operation, values)
                result = {"sol": {"res": sympy.Integer(result_value)}}
                if want_steps:
                    result["steps"] = _gcd_lcm_steps(values, action)
                return result
            return {"error": "Unsupported action: {}".format(action)}

        if request_type == "matrix":
            action, matrix = expr_info.get("action"), expr_info["value"]
            if action == "trans":
                result = {"sol": {"res": matrix.T}}
                if want_steps:
                    result["steps"] = ["Transpose rows and columns"]
                return result
            if action not in ("det", "inv"):
                return {"error": "Unsupported action: {}".format(action)}
            if not matrix.is_square:
                return {"error": "The matrix must be square"}
            determinant = simplify(matrix.det())
            if action == "det":
                result = {"sol": {"res": determinant}}
                if want_steps:
                    result["steps"] = _determinant_steps(matrix, determinant)
                return result
            if determinant == 0:
                return {"error": "Matrix is singular (det = 0)"}
            result = {"sol": {"res": matrix.inv()}}
            if want_steps:
                result["steps"] = [
                    "det = {} (not zero)".format(determinant),
                    "A^-1 = adj(A)/det",
                    "adj(A) = [{}]".format(formatter.matrix_plain(matrix.adjugate())),
                ]
            return result

        if request_type == "function":
            action = expr_info.get("action")
            if action == "define":
                name, params, body = (
                    expr_info["name"], expr_info["params"], expr_info["body"]
                )
                functions.save(name, params, body)
                return {"sol": {"msg": "{}({})={} saved".format(
                    name, ",".join(params), body
                )}}
            if action == "delete":
                if not functions.delete(expr_info["name"]):
                    return {"error": "Function not defined: " + expr_info["name"]}
                return {"sol": {"msg": expr_info["name"] + " deleted"}}
            if action == "list":
                definitions = functions.list_all()
                message = ", ".join(
                    "{}({})={}".format(name, ",".join(params), body)
                    for name, (params, body) in definitions.items()
                )
                return {"sol": {"msg": message or "no functions"}}
            return {"error": "Unsupported action: {}".format(action)}

        if request_type == "expression":
            expression, action = expr_info.get("value"), expr_info.get("action")
            if action == "simplify":
                result_value = simplify(expression)
            elif action == "expand":
                result_value = expand(expression)
            elif action == "factor":
                result_value = factor(expression)
            else:
                return {"error": "Unsupported action: {}".format(action)}
            result = {"res": result_value}
            if expr_info.get("x_value") is not None:
                result["evaluated"] = expression.subs(
                    x, expr_info["x_value"]
                ).evalf()
            output = {"sol": result}
            if want_steps:
                output["steps"] = [
                    "{}: {} -> {}".format(action, expression, result_value)
                ]
            return output

        return {"error": "Unknown expression type"}
    except Exception as exc:
        return {"error": str(exc)}
