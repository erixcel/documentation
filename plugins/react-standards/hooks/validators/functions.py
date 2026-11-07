"""Reglas de funciones React: convenciones sin clases NestJS."""
import re
from common.discovery import logic_files, text
from analyzers.imports import validate_resource_scopes


def validate_functions(root, changed):
    errors = []

    # Regla 1: Las funciones pertenecen a functions/ y terminan en .function.ts.
    issues, files = _validate_function_files(root, changed)
    errors.extend(issues)

    # Regla 2: No se permiten clases en utilidades .function.ts de React.
    errors.extend(_validate_function_no_classes(root, files))

    # Regla 3: No se permiten decoradores NestJS en funciones React.
    errors.extend(_validate_function_no_decorators(root, files))

    # Regla 4: Las funciones compartidas respetan su ámbito mínimo.
    errors.extend(_validate_function_scopes(root, changed))
    return errors


def _validate_function_files(root, changed):
    return logic_files(root, changed, "functions", ".function.ts")


def _validate_function_no_classes(root, files):
    issues = []
    for name in files:
        code = text(root, name)
        if re.search(r"(?m)^\s*(?:export\s+)?(?:abstract\s+)?class\s+", code):
            issues.append(f"{name}: [function-class] Usa funciones TypeScript, no clases NestJS.")
    return issues


def _validate_function_no_decorators(root, files):
    issues = []
    for name in files:
        code = text(root, name)
        if re.search(r"(?m)^\s*@\w+|\b@Injectable\s*\(", code):
            issues.append(f"{name}: [function-decorator] No uses decoradores NestJS en funciones React.")
    return issues


def _validate_function_scopes(root, changed):
    return validate_resource_scopes(root, changed)
