"""Reglas independientes para Controllers NestJS (sin modificar el código)."""
import re
from validators._helpers import read, named_class, class_methods, controller_dto_files


HTTP_ROUTES = {"Get", "Post", "Put", "Patch", "Delete", "Options", "Head", "All"}


def validate_controller(path):
    source, errors = read(path)
    if errors:
        return errors

    methods = class_methods(source)
    endpoints = [
        (name, decorators, body, line)
        for name, decorators, body, line in methods
        if HTTP_ROUTES & set(decorators)
    ]

    # Regla 1: La clase debe llamarse <Nombre>Controller y tener @Controller.
    errors.extend(_validate_controller_class(source, path))

    # Regla 2: Un Controller no puede depender directamente de Queries o Drizzle.
    errors.extend(_validate_controller_database_imports(source))

    # Regla 3: Los métodos del Controller requieren sus DTO correspondientes.
    errors.extend(_validate_controller_dtos(path, source))

    # Regla 4: Cada endpoint requiere documentación y orden de decoradores.
    errors.extend(_validate_controller_endpoint_decorators(endpoints))

    # Regla 5: Cada endpoint delega directamente a su Service.
    errors.extend(_validate_controller_endpoint_delegation(endpoints))

    # Regla 6: No debe existir lógica de negocio en los endpoints.
    errors.extend(_validate_controller_business_logic(endpoints))

    return errors


def _validate_controller_class(source, path):
    return named_class(source, path, ".controller.ts", "Controller", "Controller")


def _validate_controller_database_imports(source):
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", source)
    if any(path.startswith(("@db/", "@queries/")) or "drizzle-orm" in path for path in imports):
        return ["Un Controller no debe importar Drizzle, tablas ni Queries; delega al Service."]
    return []


def _validate_controller_dtos(path, source):
    return controller_dto_files(path, source)


def _validate_controller_endpoint_decorators(endpoints):
    errors = []
    for method, decorators, _body, line in endpoints:
        label = f"Línea {line} ({method})"
        if "ApiOperation" not in decorators:
            errors.append(f"{label}: falta @ApiOperation.")
        if decorators.count("ApiResponse") < 2:
            errors.append(f"{label}: requiere @ApiResponse exitoso y de error.")
        if "TraceNode" not in decorators or decorators[-1] != "TraceNode":
            errors.append(f"{label}: @TraceNode debe estar al final de los decoradores.")
        if decorators and decorators[0] not in HTTP_ROUTES:
            errors.append(f"{label}: el decorador HTTP debe ser el primero del endpoint.")
    return errors


def _validate_controller_endpoint_delegation(endpoints):
    errors = []
    for method, _decorators, body, line in endpoints:
        label = f"Línea {line} ({method})"
        if body[:2] != ["return", "this"] or not re.search(
            r"\breturn\s+this\s*\.\s*\w*[Ss]ervice\s*\.\s*\w+\s*\(", " ".join(body)
        ):
            errors.append(f"{label}: delega directamente con return this.nombreService.metodo(...).")
    return errors


def _validate_controller_business_logic(endpoints):
    errors = []
    for method, _decorators, body, line in endpoints:
        label = f"Línea {line} ({method})"
        if any(word in body for word in ("const", "let", "if", "try", "while", "for", "throw")):
            errors.append(f"{label}: el Controller no debe contener lógica de negocio.")
    return errors
