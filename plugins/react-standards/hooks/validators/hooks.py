"""Erixcel React hook validation; read-only."""
from common.discovery import logic_files
from analyzers.ast import ast_check

def validate_hooks(root, changed):
    issues, files = logic_files(root, changed, "hooks", ".hook.ts")
    issues += ast_check(root, "hooks", files)
    return issues
