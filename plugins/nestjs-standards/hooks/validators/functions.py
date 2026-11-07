"""Reglas independientes para archivos *.function.ts de NestJS."""
import re
from analyzers.query_structure import validate_one_class
from validators._helpers import read, named_class, class_methods


def validate_function(path):
    source, errors = read(path)
    if errors:
        return errors

    methods = class_methods(source)

    # Regla 1: La clase tiene el nombre y el sufijo Function correctos.
    errors.extend(_validate_function_class(source, path))

    # Regla 2: No debe haber declaraciones adicionales fuera de la clase.
    errors.extend(_validate_function_top_level(source))

    # Regla 3: Debe existir al menos un método y todos deben ser estáticos.
    errors.extend(_validate_function_static_methods(source, methods))

    # Regla 4: Cada método debe tener @TraceNode con type: 'method'.
    errors.extend(_validate_function_trace_nodes(source, methods))

    # Regla 5: Una Function no declara endpoints ni providers NestJS.
    errors.extend(_validate_function_nestjs_decorators(source))

    # Regla 6: Las Functions no deben consultar tablas directamente.
    errors.extend(_validate_function_database_imports(source))

    # Regla 7: TraceNode se importa desde @erixcel/traceflow.
    errors.extend(_validate_function_traceflow_import(source))

    return errors


def _validate_function_class(source, path):
    return named_class(source, path, ".function.ts", "Function")


def _validate_function_top_level(source):
    return [issue.replace(".query.ts", ".function.ts") for issue in validate_one_class(source)]


def _validate_function_static_methods(source, methods):
    errors = []
    if not methods:
        errors.append("Un .function.ts debe contener al menos un método static.")
    for name, decorators, _body, line in methods:
        label = f"Línea {line} ({name})"
        signature = r"\bstatic\s+(?:async\s+)?" + re.escape(name) + r"\s*(?:<[^>]+>)?\s*\("
        if not re.search(signature, source):
            errors.append(f"{label}: todos los métodos deben ser static.")
    return errors


def _validate_function_trace_nodes(source, methods):
    errors = []
    for name, decorators, _body, line in methods:
        label = f"Línea {line} ({name})"
        if "TraceNode" not in decorators:
            errors.append(f"{label}: falta @TraceNode({{ name: '...', type: 'method' }}).")
        else:
            signature = (
                r"@TraceNode\s*\(\s*\{[^}]*\btype\s*:\s*['\"]method['\"][^}]*\}\s*\)\s*"
                r"(?:(?:public|private|protected|static|async)\s+)*"
                + re.escape(name) + r"\s*(?:<[^>]+>)?\s*\("
            )
            if not re.search(signature, source, re.S):
                errors.append(f"{label}: @TraceNode debe usar type: 'method' e ir antes del método static.")
    return errors


def _validate_function_nestjs_decorators(source):
    if re.search(r"@(?:Controller|Get|Post|Module|Injectable)\s*\(", source):
        return ["Una Function no debe declarar endpoints ni registrar providers NestJS."]
    return []


def _validate_function_database_imports(source):
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", source)
    if any(path.startswith(("@db/tables/", "@db/connection")) for path in imports):
        return ["Las Functions no deben consultar tablas: usa la capa Queries."]
    return []


def _validate_function_traceflow_import(source):
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", source)
    if "traceflow" in imports:
        return ["Importa TraceNode desde '@erixcel/traceflow', no desde 'traceflow'."]
    return []
