"""Reglas para servicios React independientes y sus operaciones."""
import re
from common.discovery import logic_files, text
from analyzers.ast import ast_check
from validators.api import validate_api


def validate_services(root, changed):
    errors = []

    # Regla 1: Los servicios usan services/ y el sufijo .service.ts.
    issues, files = _validate_service_files(root, changed)
    errors.extend(issues)

    # Regla 2: Los servicios de Vite no deben usar process.env.
    errors.extend(_validate_service_environment(root, files))

    # Regla 3: El AST de servicios debe contener solo imports y funciones.
    errors.extend(_validate_service_ast(root, files))
    return errors


def _validate_service_files(root, changed):
    return logic_files(root, changed, "services", ".service.ts")


def _validate_service_environment(root, files):
    issues = []
    for name in files:
        if re.search(r"\bprocess\.env\b", text(root, name)):
            issues.append(f"{name}: usa import.meta.env en Vite, no process.env.")
    return issues


def _validate_service_ast(root, files):
    return ast_check(root, "services", files)


def validate_api_services(root, changed):
    """Compatibilidad con el comando manual 'api-services'."""
    return validate_api(root, changed) + validate_services(root, changed)
