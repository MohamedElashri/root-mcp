"""Expression evaluation utilities."""

from __future__ import annotations

import ast
import re
from typing import Any

import numpy as np


def strip_outer_parens(expr: str) -> str:
    """Strip outer parentheses from expression."""
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        depth = 0
        ok = True
        for i, ch in enumerate(expr):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(expr) - 1:
                    ok = False
                    break
        if not ok:
            break
        expr = expr[1:-1].strip()
    return expr


def translate_leaf_expr(expr: str) -> str:
    """Translate C++ style expression to Python."""
    expr = expr.strip()
    expr = expr.replace("&&", "&").replace("||", "|")
    expr = re.sub(r"!(?!=)", "~", expr)
    expr = re.sub(r"\btrue\b", "True", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bfalse\b", "False", expr, flags=re.IGNORECASE)
    return expr


class SafeExprEvaluator(ast.NodeVisitor):
    """
    Safe expression evaluator for limited math subset.
    Uses abstract syntax tree to evaluate expressions without eval().
    """

    def __init__(self, names: dict[str, Any]):
        """
        Initialize evaluator.

        Args:
            names: Dictionary of allowed variable names and their values
        """
        self.names = names
        self.funcs: dict[str, Any] = {
            "abs": np.abs,
            "sqrt": np.sqrt,
            "log": np.log,
            "exp": np.exp,
            "sin": np.sin,
            "cos": np.cos,
            "tan": np.tan,
            "min": np.minimum,
            "max": np.maximum,
            "sinh": np.sinh,
            "cosh": np.cosh,
            "tanh": np.tanh,
            "arcsin": np.arcsin,
            "arccos": np.arccos,
            "arctan": np.arctan,
            "arctan2": np.arctan2,
        }

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.names:
            return self.names[node.id]
        if node.id in {"True", "False"}:
            return node.id == "True"
        if node.id in self.funcs:
            return self.funcs[node.id]
        raise ValueError(f"Unknown identifier in expression: {node.id}")

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.Invert):
            return ~operand
        raise ValueError("Unsupported unary operator")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.Pow):
            return left**right
        if isinstance(op, ast.Mod):
            return left % right
        if isinstance(op, ast.BitAnd):
            return left & right
        if isinstance(op, ast.BitOr):
            return left | right
        raise ValueError("Unsupported binary operator")

    def visit_Compare(self, node: ast.Compare) -> Any:
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError("Chained comparisons are not supported")

        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        op = node.ops[0]
        if isinstance(op, ast.Lt):
            return left < right
        if isinstance(op, ast.LtE):
            return left <= right
        if isinstance(op, ast.Gt):
            return left > right
        if isinstance(op, ast.GtE):
            return left >= right
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        raise ValueError("Unsupported comparison operator")

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed")
        fn = self.visit_Name(node.func)
        if fn not in self.funcs.values():
            raise ValueError(f"Function '{node.func.id}' is not allowed")
        if node.keywords:
            raise ValueError("Keyword arguments are not supported")
        args = [self.visit(a) for a in node.args]
        return fn(*args)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported syntax in expression: {type(node).__name__}")
