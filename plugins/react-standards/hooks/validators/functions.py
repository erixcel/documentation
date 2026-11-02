"""Erixcel React hook validation; read-only."""
import re
from common.discovery import logic_files, text
from analyzers.imports import validate_resource_scopes

def validate_functions(root, changed):
    issues, files = logic_files(root, changed, "functions", ".function.ts")
    for name in files:
        code = text(root, name)
        # Conservative syntax scan; TypeScript AST rules are also applied to hooks/services.
        if re.search(r"(?m)^\s*(?:export\s+)?(?:abstract\s+)?class\s+", code):
            issues.append(f"{name}: [function-class] Usa funciones TypeScript, no clases NestJS.")
        if re.search(r"(?m)^\s*@\w+|\b@Injectable\s*\(", code):
            issues.append(f"{name}: [function-decorator] No uses decoradores NestJS en funciones React.")
    return issues + validate_resource_scopes(root, changed)
