"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

def validate_controller(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".controller.ts", "Controller", "Controller")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith(("@db/", "@queries/")) or "drizzle-orm" in p for p in imports):
        errors.append("Un Controller no debe importar Drizzle, tablas ni Queries; delega al Service.")
    methods = class_methods(s)
    errors += controller_dto_files(path, s)
    routes = {"Get", "Post", "Put", "Patch", "Delete", "Options", "Head", "All"}
    for method, decorators, body, line in methods:
        if not (routes & set(decorators)):
            continue
        label = f"Línea {line} ({method})"
        if "ApiOperation" not in decorators:
            errors.append(f"{label}: falta @ApiOperation.")
        if decorators.count("ApiResponse") < 2:
            errors.append(f"{label}: requiere @ApiResponse exitoso y de error.")
        if "TraceNode" not in decorators or decorators[-1] != "TraceNode":
            errors.append(f"{label}: @TraceNode debe estar al final de los decoradores.")
        if decorators and decorators[0] not in routes:
            errors.append(f"{label}: el decorador HTTP debe ser el primero del endpoint.")
        if body[:2] != ["return", "this"] or not re.search(
            r"\breturn\s+this\s*\.\s*\w*[Ss]ervice\s*\.\s*\w+\s*\(", " ".join(body)
        ):
            errors.append(f"{label}: delega directamente con return this.nombreService.metodo(...).")
        if any(x in body for x in ("const", "let", "if", "try", "while", "for", "throw")):
            errors.append(f"{label}: el Controller no debe contener lógica de negocio.")
    return errors
