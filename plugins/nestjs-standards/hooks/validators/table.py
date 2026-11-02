"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

def validate_table(path):
    s, errors = read(path)
    if errors:
        return errors
    count = len(re.findall(r"\bpgTable\s*\(", s))
    if count != 1:
        errors.append(f"Un archivo .table.ts define exactamente una tabla pgTable (encontradas {count}).")
    fields = {
        "createdAt": ("created_at", True),
        "updatedAt": ("updated_at", True),
        "deletedAt": ("deleted_at", False),
    }
    for field, (column, required) in fields.items():
        regex = r"\b" + field + r"\s*:\s*timestamp\s*\(\s*['\"]" + column + r"['\"]\s*\)"
        match = re.search(regex, s)
        if not match:
            errors.append(f"Falta {field}: timestamp('{column}') en inglés.")
        elif required and not re.match(r"\s*\.defaultNow\s*\(\s*\)\s*\.notNull\s*\(\s*\)", s[match.end():]):
            errors.append(f"{field} requiere .defaultNow().notNull().")
    if not re.search(r"\bexport\s+const\s+\w+\s*=\s*pgTable\s*\(", s):
        errors.append("Exporta la definición principal con export const ... = pgTable(...).")
    for name in ("$inferSelect", "$inferInsert"):
        if name not in s:
            errors.append(f"Exporta un tipo Drizzle basado en {name}.")
    return errors
