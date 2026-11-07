"""Reglas para Query y JoinQuery de Erixcel NestJS."""
import re
from analyzers.query_structure import validate_one_class


JOIN_RE = re.compile(r"\.\s*(?:leftJoin|rightJoin|innerJoin|fullJoin|crossJoin)\s*\(")
WRITE_RE = re.compile(r"\.\s*(?:insert|update|delete)\s*\(")
IMPORT_RE = re.compile(r'''(?m)^[ \t]*import\b[\s\S]*?\bfrom\s*['"]([^'"]+)['"]''')


def validate_query(path):
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"No se pudo leer: {exc}"]

    code = re.sub(r"/\*[\s\S]*?\*/|(?m:^[ \t]*//[^\n]*)", "", source)
    modules = [match.group(1) for match in IMPORT_RE.finditer(code)]
    tables = sorted(set(module for module in modules if module.endswith((".table", ".table.ts", ".table.js"))))
    issues = []

    # Regla 1: Solo imports, decoradores y una clase Query por archivo.
    issues.extend(_validate_query_class(source))

    if path.name.endswith("-join.query.ts"):
        # Regla 2: Los archivos JoinQuery son de solo lectura.
        issues.extend(_validate_join_query_read_only(code))
    else:
        # Regla 3: Los archivos Query importan exactamente una tabla base.
        issues.extend(_validate_query_single_table(tables))

        # Regla 4: Los JOIN solo se permiten en -join.query.ts.
        issues.extend(_validate_query_no_joins(code))

    return issues


def _validate_query_class(source):
    return validate_one_class(source)


def _validate_join_query_read_only(code):
    issues = []
    for match in WRITE_RE.finditer(code):
        line = code.count("\n", 0, match.start()) + 1
        issues.append(f"Línea {line}: -join.query.ts es solo SELECT; no admite operaciones de escritura.")
    return issues


def _validate_query_single_table(tables):
    if len(tables) != 1:
        return [f".query.ts debe importar solo una tabla *.table (encontradas {len(tables)}): {', '.join(tables) or 'ninguna'}."]
    return []


def _validate_query_no_joins(code):
    issues = []
    for match in JOIN_RE.finditer(code):
        line = code.count("\n", 0, match.start()) + 1
        issues.append(f"Línea {line}: JOIN prohibido en .query.ts; utilice -join.query.ts.")
    return issues
