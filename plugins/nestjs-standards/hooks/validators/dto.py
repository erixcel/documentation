"""Validaciones independientes para archivos DTO de Erixcel NestJS."""
import re

from validators._helpers import class_names, read


def validate_dto(path):
    """Ejecuta cada regla del DTO y reúne todos los errores encontrados."""
    source, errors = read(path)
    if errors:
        return errors

    names = class_names(source)

    # Regla 1: El archivo debe usar kebab-case y terminar en .dto.ts.
    errors.extend(_validate_dto_filename(path))

    # Regla 2: Debe existir al menos una clase y todas deben terminar en Dto.
    errors.extend(_validate_dto_classes(names))

    # Regla 3: Cada clase DTO debe declarar @Trace({ type: 'validation' }).
    errors.extend(_validate_dto_traces(source, names))

    # Regla 4: Un DTO no debe importar Queries ni conexiones de base de datos.
    errors.extend(_validate_dto_database_imports(source))

    # Regla 5: Un DTO no debe ejecutar operaciones Drizzle directamente.
    errors.extend(_validate_dto_database_queries(source))

    return errors


def _validate_dto_filename(path):
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.dto\.ts", path.name):
        return ["Nombre de DTO: kebab-case y sufijo .dto.ts."]
    return []


def _validate_dto_classes(names):
    errors = []
    if not names:
        errors.append("El DTO debe declarar una o más clases.")
    for name in names:
        if not name.endswith("Dto"):
            errors.append(f"La clase {name} debe terminar en Dto.")
    return errors


def _validate_dto_traces(source, names):
    traces = len(re.findall(
        r"@Trace\s*\(\s*\{[^}]*\btype\s*:\s*['\"]validation['\"]",
        source,
        re.S,
    ))
    if names and traces < len(names):
        return ["Cada clase DTO debe llevar @Trace({ type: 'validation' })."]
    return []


def _validate_dto_database_imports(source):
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", source)
    if any(p.startswith(("@queries/", "@db/connection", "@db/config")) for p in imports):
        return ["Los DTO no deben consultar la base de datos ni depender de su conexión."]
    return []


def _validate_dto_database_queries(source):
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", source):
        return ["Las consultas no pertenecen a los DTO."]
    return []
