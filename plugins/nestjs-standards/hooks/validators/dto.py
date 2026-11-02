"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

def validate_dto(path):
    s, errors = read(path)
    if errors:
        return errors
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.dto\.ts", path.name):
        errors.append("Nombre de DTO: kebab-case y sufijo .dto.ts.")
    names = class_names(s)
    if not names:
        errors.append("El DTO debe declarar una o más clases.")
    for name in names:
        if not name.endswith("Dto"):
            errors.append(f"La clase {name} debe terminar en Dto.")
    traces = len(re.findall(r"@Trace\s*\(\s*\{[^}]*\btype\s*:\s*['\"]validation['\"]", s, re.S))
    if names and traces < len(names):
        errors.append("Cada clase DTO debe llevar @Trace({ type: 'validation' }).")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith(("@queries/", "@db/connection", "@db/config")) for p in imports):
        errors.append("Los DTO no deben consultar la base de datos ni depender de su conexión.")
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", s):
        errors.append("Las consultas no pertenecen a los DTO.")
    return errors
