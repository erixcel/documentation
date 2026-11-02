"""Erixcel NestJS modular static hook validators; read-only."""
"""Static NestJS convention checks based on Erixcel documentation.

Heuristic, stdlib-only; no project writes, imports or execution.
"""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens

IDENT = re.compile(r"^[A-Za-z_$][\w$]*$")


def read(path):
    try:
        return path.read_text(encoding="utf-8"), []
    except (OSError, UnicodeError) as exc:
        return "", [f"No se pudo leer: {exc}"]


def class_names(source):
    """Only module-scope class declarations, not classes nested in methods."""
    items = tokens(source)
    depth = 0
    names = []
    for i, (value, _line) in enumerate(items):
        if depth == 0 and value == "class" and i + 1 < len(items):
            if IDENT.fullmatch(items[i + 1][0]):
                names.append(items[i + 1][0])
        if value == "{":
            depth += 1
        elif value == "}":
            depth = max(0, depth - 1)
    return names


def pascal(stem):
    return "".join(chunk[:1].upper() + chunk[1:] for chunk in re.split(r"[-_]", stem) if chunk)


def named_class(source, path, suffix, expected_suffix, require_decorator=None):
    errors = []
    classes = class_names(source)
    expected = pascal(path.name[:-len(suffix)]) + expected_suffix
    if classes != [expected]:
        errors.append(
            f"Debe haber exactamente una clase llamada {expected}; encontradas {classes or 'ninguna'}."
        )
    if require_decorator and not re.search(
        r"@" + re.escape(require_decorator) + r"\s*\(", source
    ):
        errors.append(f"Falta @{require_decorator} en {path.name}.")
    return errors


def class_methods(source):
    """Find decorators and method bodies of the first top-level class.

    Uses balanced TS tokens. Does not execute TypeScript.
    """
    t = tokens(source)
    depth = 0
    begin = None
    for i, (value, _) in enumerate(t):
        if depth == 0 and value == "class":
            begin = next((j for j in range(i + 1, len(t)) if t[j][0] == "{"), None)
            break
        if value == "{":
            depth += 1
        elif value == "}":
            depth = max(0, depth - 1)
    if begin is None:
        return []
    result = []
    i = begin + 1
    depth = 1
    pending = []
    while i < len(t) and depth > 0:
        word, line = t[i]
        if depth == 1 and word == "@":
            j = i + 1
            decorator = t[j][0] if j < len(t) else ""
            while j < len(t) and (IDENT.fullmatch(t[j][0]) or t[j][0] == "."):
                j += 1
            if j < len(t) and t[j][0] == "(":
                level = 0
                while j < len(t):
                    v = t[j][0]
                    if v == "(":
                        level += 1
                    elif v == ")":
                        level -= 1
                        if level == 0:
                            j += 1
                            break
                    j += 1
            pending.append(decorator)
            i = j
            continue
        if depth == 1 and word == "(" and i > 0:
            # For generic methods foo<T>(...) find the identifier before <T>.
            method_index = i - 1
            if t[method_index][0] == ">":
                generic_depth = 1
                method_index -= 1
                while method_index >= 0 and generic_depth > 0:
                    value = t[method_index][0]
                    if value == ">":
                        generic_depth += 1
                    elif value == "<":
                        generic_depth -= 1
                    method_index -= 1
            method = t[method_index][0] if method_index >= 0 else ""
            if not IDENT.fullmatch(method):
                i += 1
                continue
            if method in {"if", "for", "while", "switch", "catch", "constructor"}:
                pending = []
            j = i
            level = 0
            while j < len(t):
                v = t[j][0]
                if v == "(":
                    level += 1
                elif v == ")":
                    level -= 1
                    if level == 0:
                        j += 1
                        break
                j += 1
            while j < len(t) and t[j][0] not in ("{", ";"):
                j += 1
            if j < len(t) and t[j][0] == "{":
                start = j + 1
                inside = 1
                j = start
                while j < len(t) and inside:
                    v = t[j][0]
                    if v == "{":
                        inside += 1
                    elif v == "}":
                        inside -= 1
                    j += 1
                if method != "constructor":
                    result.append((method, pending[:], [v for v, _ in t[start:j - 1]], line))
                pending = []
                i = j
                continue
        if word == "{":
            depth += 1
        elif word == "}":
            depth -= 1
        elif word == ";" and depth == 1:
            pending = []
        i += 1
    return result


def controller_dto_files(path, source):
    """Require dto/<method-in-kebab-case>.dto.ts for each method, except constructor.

    Controllers in one module folder share a single DTO directory, so the expected
    filenames are the union across those Controllers.
    """
    folder = path.parent / "dto"
    required = set()
    for candidate in sorted(path.parent.glob("*.controller.ts")):
        code = source if candidate == path else candidate.read_text(encoding="utf-8")
        for method, _decorators, _body, _line in class_methods(code):
            stem = re.sub(r"([A-Z])([A-Z][a-z])", r"\1-\2", method)
            stem = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", stem)
            required.add(stem.replace("_", "-").lower() + ".dto.ts")
    actual = {p.name for p in folder.glob("*.dto.ts") if p.is_file()} if folder.is_dir() else set()
    missing = sorted(required - actual)
    extras = sorted(actual - required)
    errors = []
    if missing:
        errors.append(
            f"DTO faltantes en {folder}: {', '.join(missing)}. "
            "Cada método del Controller (excepto constructor) necesita exactamente "
            "un archivo dto/<metodo-en-kebab-case>.dto.ts."
        )
    if extras:
        errors.append(
            f"DTO sobrantes en {folder}: {', '.join(extras)}. "
            "Conserva los contratos existentes: primero migra clases, imports y referencias "
            "a los DTO de métodos; luego retira los archivos sobrantes si es seguro."
        )
    return errors
