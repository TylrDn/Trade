"""Structural contract tests for live strategy gateway invariants.

These tests catch accidental direct order submission in reference strategies.
They do not replace OMS-level enforcement.
"""

from __future__ import annotations

import ast
from pathlib import Path

EMA_CROSS_PATH = Path(__file__).resolve().parents[1] / "nautilus_trade/strategies/ema_cross.py"


def _call_self_method(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        if node.func.value.id == "self":
            return node.func.attr
    return None


def _find_class_method(tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == method_name:
                return item
    raise AssertionError(f"{class_name}.{method_name} not found")


def _nested_function(method: ast.FunctionDef, name: str) -> ast.FunctionDef:
    for node in ast.walk(method):
        if isinstance(node, ast.FunctionDef) and node.name == name and node is not method:
            return node
    raise AssertionError(f"nested function {name} not found in {method.name}")


def _self_calls_in_subtree(root: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(root):
        if isinstance(node, ast.Call):
            method = _call_self_method(node)
            if method is not None:
                names.append(method)
    return names


def _calls_of(method: ast.FunctionDef, attr: str) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(method):
        if isinstance(node, ast.Call) and _call_self_method(node) == attr:
            calls.append(node)
    return calls


def _is_under(node: ast.AST, ancestor: ast.AST) -> bool:
    for child in ast.walk(ancestor):
        if child is node:
            return True
    return False


class TestEmaCrossGatewayContract:
    def test_ema_cross_uses_guarded_submission_paths(self) -> None:
        tree = ast.parse(EMA_CROSS_PATH.read_text(encoding="utf-8"))
        on_bar = _find_class_method(tree, "EmaCrossStrategy", "on_bar")
        on_stop = _find_class_method(tree, "EmaCrossStrategy", "on_stop")

        submit_entry = _nested_function(on_bar, "submit_entry")
        submit_exit = _nested_function(on_bar, "submit_exit")

        on_bar_methods = _self_calls_in_subtree(on_bar)
        assert "submit_order_guarded" in on_bar_methods
        assert "submit_exit_guarded" in on_bar_methods

        for call in _calls_of(on_bar, "submit_order"):
            assert _is_under(call, submit_entry), (
                "self.submit_order must only appear inside submit_entry nested function"
            )

        for call in _calls_of(on_bar, "close_position"):
            assert _is_under(call, submit_exit), (
                "self.close_position must only appear inside submit_exit nested function"
            )

        forbidden_in_on_bar = {"close_all_positions", "submit_order", "close_position"}
        for name in forbidden_in_on_bar:
            for call in _calls_of(on_bar, name):
                if name == "submit_order" and _is_under(call, submit_entry):
                    continue
                if name == "close_position" and _is_under(call, submit_exit):
                    continue
                raise AssertionError(f"unexpected self.{name} in on_bar outside guarded nested fn")

        on_stop_order_methods = {
            name
            for name in _self_calls_in_subtree(on_stop)
            if name in {"submit_order", "close_position", "close_all_positions"}
        }
        assert on_stop_order_methods == {"close_all_positions"}, (
            "on_stop may only call close_all_positions among order/position submission APIs "
            f"(found {on_stop_order_methods})"
        )

    def test_documented_bypasses_exist_in_source(self) -> None:
        source = EMA_CROSS_PATH.read_text(encoding="utf-8")
        assert "gateway is None" in source
        assert "flatten_on_stop" in source
        assert "close_all_positions" in source
