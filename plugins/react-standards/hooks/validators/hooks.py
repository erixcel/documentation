"""Reglas de nomenclatura y AST para React hooks."""
from common.discovery import logic_files
from analyzers.ast import ast_check


def validate_hooks(root, changed):
    errors = []

    # Regla 1: Los hooks se ubican en hooks/ y terminan en .hook.ts.
    issues, files = _validate_hook_files(root, changed)
    errors.extend(issues)

    # Regla 2: El AST permite solo imports y funciones en cada hook.
    errors.extend(_validate_hook_ast(root, files))
    return errors


def _validate_hook_files(root, changed):
    return logic_files(root, changed, "hooks", ".hook.ts")


def _validate_hook_ast(root, files):
    return ast_check(root, "hooks", files)
