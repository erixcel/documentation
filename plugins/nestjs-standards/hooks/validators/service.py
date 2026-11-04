"""Erixcel NestJS Service Validator: one exported Injectable class per file."""
import re

from analyzers.query_structure import tokens, validate_one_class
from validators._helpers import named_class, read


def has_exported_service_class(source):
    """Check exports at module scope, ignoring strings, comments and method bodies."""
    items = tokens(source)
    braces = 0
    for i, (value, _) in enumerate(items):
        if braces == 0 and value == "export":
            j = i + 1
            if j < len(items) and items[j][0] == "default":
                j += 1
            if j < len(items) and items[j][0] == "class":
                return True
        if value == "{":
            braces += 1
        elif value == "}":
            braces = max(0, braces - 1)
    return False


def validate_service(path):
    source, errors = read(path)
    if errors:
        return errors

    errors.extend(named_class(source, path, ".service.ts", "Service", "Injectable"))
    errors.extend(validate_one_class(source, file_type="service"))
    if not has_exported_service_class(source):
        errors.append(
            "[service-single-class] Exporta exactamente una clase "
            "<Nombre>Service con export class (o export default class)."
        )

    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", source)
    if any(p.startswith("@db/") or "drizzle-orm" in p for p in imports):
        errors.append("El Service debe acceder a datos mediante Queries, no mediante Drizzle o tablas.")
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", source):
        errors.append("El Service no debe ejecutar consultas Drizzle directamente.")
    if re.search(r"@(?:Controller|Get|Post|Patch|Delete)\s*\(", source):
        errors.append("Las rutas HTTP corresponden al Controller, no al Service.")
    return errors
