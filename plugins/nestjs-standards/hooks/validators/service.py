"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

def validate_service(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".service.ts", "Service", "Injectable")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith("@db/") or "drizzle-orm" in p for p in imports):
        errors.append("El Service debe acceder a datos mediante Queries, no mediante Drizzle o tablas.")
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", s):
        errors.append("El Service no debe ejecutar consultas Drizzle directamente.")
    if re.search(r"@(?:Controller|Get|Post|Patch|Delete)\s*\(", s):
        errors.append("Las rutas HTTP corresponden al Controller, no al Service.")
    return errors
