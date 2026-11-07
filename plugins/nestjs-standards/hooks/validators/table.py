"""Reglas independientes de tablas Drizzle *.table.ts para Erixcel NestJS."""
import re
from analyzers.query_structure import tokens
from validators._helpers import read


def validate_table(path):
    source, errors = read(path)
    if errors:
        return errors

    # Regla 1: Solo pgEnum y una declaración exportada pgTable, sin types/helpers.
    errors.extend(_validate_table_declarations(source))

    # Regla 2: Debe existir exactamente una llamada principal a pgTable.
    errors.extend(_validate_table_single_pgtable(source))

    # Regla 3: createdAt debe existir con defaultNow y notNull.
    errors.extend(_validate_table_audit_field(source, "createdAt", "created_at", required=True))

    # Regla 4: updatedAt debe existir con defaultNow y notNull.
    errors.extend(_validate_table_audit_field(source, "updatedAt", "updated_at", required=True))

    # Regla 5: deletedAt debe existir como columna de auditoría anulable.
    errors.extend(_validate_table_audit_field(source, "deletedAt", "deleted_at", required=False))

    return errors


def _validate_table_declarations(source):
    """Validate declarations with lexical tokens, ignoring comments and strings.

    Track grouping so that words inside Drizzle definitions do not count as
    module declarations; local const/let/var declarations are disallowed too.
    """
    items = tokens(source)
    depths = []
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for value, _ in items:
        depths.append(len(stack))
        if value in ("(", "[", "{"):
            stack.append(value)
        elif value in pairs and stack and stack[-1] == pairs[value]:
            stack.pop()

    errors = []
    exported_tables = 0
    for i, (word, line) in enumerate(items):
        depth = depths[i]
        before = items[i - 1][0] if i else None

        # "as const" is a TS assertion, not a variable declaration.
        if word == "const" and before == "as":
            continue
        if word == "const":
            exported = depth == 0 and before == "export" and depths[i - 1] == 0
            name = items[i + 1][0] if i + 1 < len(items) else ""
            assignment = items[i + 2][0] if i + 2 < len(items) else ""
            factory = items[i + 3][0] if i + 3 < len(items) else ""
            call = items[i + 4][0] if i + 4 < len(items) else ""
            is_named = bool(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name))
            is_allowed = (
                depth == 0 and is_named and assignment == "=" and call == "("
                and (factory == "pgEnum" or (exported and factory == "pgTable"))
            )
            if is_allowed and factory == "pgTable":
                exported_tables += 1
            if not is_allowed:
                errors.append(
                    f"Línea {line}: [table-declaration] const no permitido. "
                    "Solo admite const = pgEnum(...) y export const = pgTable(...); "
                    "usa timestamp(...) directamente en cada columna."
                )
        elif word in ("let", "var"):
            errors.append(
                f"Línea {line}: [table-declaration] {word} no permitido en *.table.ts."
            )
        elif word in ("type", "interface", "enum"):
            # import type { X } is allowed; type in a column object is a key,
            # not a declaration. An 'enum' keyword is not a pgEnum call.
            if word == "type" and before == "import":
                continue
            if word == "type" and before in ("{", ",") and depth > 0:
                continue
            candidate = items[i + 1][0] if i + 1 < len(items) else ""
            next_word = items[i + 2][0] if i + 2 < len(items) else ""
            if depth == 0 or (
                re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", candidate)
                and next_word in ("=", "{", "<", "extends")
            ):
                errors.append(
                    f"Línea {line}: [table-type] No declares {word} en *.table.ts. "
                    "Coloca contratos/tipos fuera del archivo de tabla."
                )
        elif word == "export" and depth == 0:
            next_word = items[i + 1][0] if i + 1 < len(items) else ""
            if next_word != "const":
                errors.append(
                    f"Línea {line}: [table-export] Solo exporta const de pgTable o pgEnum; "
                    "no exportes types, interfaces, funciones ni reexports."
                )
        elif word in ("function", "class", "namespace", "declare") and depth == 0:
            errors.append(
                f"Línea {line}: [table-declaration] {word} no permitido en *.table.ts."
            )

    if exported_tables != 1:
        errors.append(
            "Exporta exactamente una definición principal con export const ... = pgTable(...)."
        )
    return errors


def _validate_table_single_pgtable(source):
    parsed = tokens(source)
    count = sum(
        word == "pgTable" and i + 1 < len(parsed) and parsed[i + 1][0] == "("
        for i, (word, _) in enumerate(parsed)
    )
    if count != 1:
        return [f"Un archivo .table.ts define exactamente una tabla pgTable (encontradas {count})."]
    return []


def _validate_table_audit_field(source, field, column, required):
    # Se admiten timestamp('name') y timestamp('name', { withTimezone: true }).
    pattern = (
        r"\b" + field + r"\s*:\s*timestamp\s*\(\s*['\"]"
        + column + r"['\"]\s*(?:,\s*\{[^{}]*\}\s*)?\)"
    )
    match = re.search(pattern, source)
    if not match:
        return [
            f"Falta {field}: usa timestamp('{column}') directamente "
            "y opcionalmente { withTimezone: true }."
        ]
    if required and not re.match(
        r"\s*\.defaultNow\s*\(\s*\)\s*\.notNull\s*\(\s*\)",
        source[match.end():],
    ):
        return [f"{field} requiere .defaultNow().notNull()."]
    return []
