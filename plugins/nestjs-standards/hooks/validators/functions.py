"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

def validate_function(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".function.ts", "Function")
    from query_structure import validate_one_class
    errors += [
        issue.replace(".query.ts", ".function.ts")
        for issue in validate_one_class(s)
    ]
    methods = class_methods(s)
    if not methods:
        errors.append("Un .function.ts debe contener al menos un método static.")
    for name, decorators, _body, line in methods:
        label = f"Línea {line} ({name})"
        static_signature = r"\bstatic\s+(?:async\s+)?" + re.escape(name) + r"\s*(?:<[^>]+>)?\s*\("
        if not re.search(static_signature, s):
            errors.append(f"{label}: todos los métodos deben ser static.")
        if "TraceNode" not in decorators:
            errors.append(f"{label}: falta @TraceNode({{ name: '...', type: 'method' }}).")
        else:
            trace_signature = (
                r"@TraceNode\s*\(\s*\{[^}]*\btype\s*:\s*['\"]method['\"][^}]*\}\s*\)\s*"
                r"(?:(?:public|private|protected|static|async)\s+)*" +
                re.escape(name) + r"\s*(?:<[^>]+>)?\s*\("
            )
            if not re.search(trace_signature, s, re.S):
                errors.append(f"{label}: @TraceNode debe usar type: 'method' e ir antes del método static.")
    if re.search(r"@(?:Controller|Get|Post|Module|Injectable)\s*\(", s):
        errors.append("Una Function no debe declarar endpoints ni registrar providers NestJS.")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith(("@db/tables/", "@db/connection")) for p in imports):
        errors.append("Las Functions no deben consultar tablas: usa la capa Queries.")
    if "traceflow" in imports:
        errors.append("Importa TraceNode desde '@erixcel/traceflow', no desde 'traceflow'.")
    return errors
