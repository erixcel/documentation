"""Reglas independientes para archivos *.service.ts de NestJS."""
import re
from analyzers.query_structure import tokens, validate_one_class
from validators._helpers import named_class, read


def validate_service(path):
    source, errors = read(path)
    if errors:
        return errors

    # Regla 1: Nombre de clase Service y decorador @Injectable correctos.
    errors.extend(_validate_service_class(source, path))

    # Regla 2: Solo imports, decoradores y una clase Service a nivel superior.
    errors.extend(_validate_service_top_level(source))

    # Regla 3: No declarar type/interface/enum en el archivo Service.
    errors.extend(_validate_service_local_contracts(source))

    # Regla 4: La única clase Service debe estar exportada.
    errors.extend(_validate_service_export(source))

    # Regla 5: Los Services acceden a datos mediante Queries, no Drizzle directo.
    errors.extend(_validate_service_database_imports(source))

    # Regla 6: No ejecutar operaciones de base de datos directamente.
    errors.extend(_validate_service_database_calls(source))

    # Regla 7: Decoradores de rutas HTTP solo en Controllers.
    errors.extend(_validate_service_http_routes(source))

    return errors


def _validate_service_class(source, path):
    return named_class(source, path, ".service.ts", "Service", "Injectable")


def _validate_service_top_level(source):
    return validate_one_class(source, file_type="service")


def _validate_service_local_contracts(source):
    """Reject type/interface/enum declarations even if nested in service methods.

    Preserve type annotations, generic usages, 'type' object keys, and import type.
    """
    items = tokens(source)
    errors = []
    for i, (word, line) in enumerate(items):
        if word not in ("type", "interface", "enum"):
            continue
        after_name = items[i + 2][0] if i + 2 < len(items) else ""
        name = items[i + 1][0] if i + 1 < len(items) else ""
        if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name):
            continue
        is_declaration = (
            word == "type" and after_name in ("=", "<")
            or word == "interface" and after_name in ("{", "<", "extends")
            or word == "enum" and after_name == "{"
        )
        if is_declaration:
            errors.append(
                f"Línea {line}: [service-no-types] declaración {word} {name} "
                "no permitida en *.service.ts; mueve los contratos fuera del Service."
            )
    return errors


def _validate_service_export(source):
    if not _service_has_exported_class(source):
        return [
            "[service-single-class] Exporta exactamente una clase "
            "<Nombre>Service con export class (o export default class)."
        ]
    return []


def _service_has_exported_class(source):
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


def _validate_service_database_imports(source):
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", source)
    if any(path.startswith("@db/") or "drizzle-orm" in path for path in imports):
        return ["El Service debe acceder a datos mediante Queries, no mediante Drizzle o tablas."]
    return []


def _validate_service_database_calls(source):
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", source):
        return ["El Service no debe ejecutar consultas Drizzle directamente."]
    return []


def _validate_service_http_routes(source):
    if re.search(r"@(?:Controller|Get|Post|Patch|Delete)\s*\(", source):
        return ["Las rutas HTTP corresponden al Controller, no al Service."]
    return []
