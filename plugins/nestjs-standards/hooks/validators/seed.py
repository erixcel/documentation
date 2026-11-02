"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from validators._helpers import read, named_class, class_names, class_methods, pascal, IDENT

def validate_seed_directory(folder):
    """Only *.seed.ts files directly in src/seeds; no other files or folders."""
    if not folder.is_dir():
        return []
    invalid_files = sorted(
        entry.name for entry in folder.iterdir()
        if not entry.is_dir() and not (
            entry.is_file() and not entry.is_symlink()
            and entry.name.endswith(".seed.ts")
        )
    )
    invalid_dirs = sorted(entry.name + "/" for entry in folder.iterdir() if entry.is_dir())
    problems = []
    if invalid_files:
        problems.append(
            "Archivos no permitidos directamente en " + str(folder)
            + ": " + ", ".join(invalid_files)
            + ". Solo archivos *.seed.ts. Guarda los datos iniciales dentro "
              "de la función seed correspondiente."
        )
    if invalid_dirs:
        problems.append(
            "Subcarpetas prohibidas dentro de " + str(folder)
            + ": " + ", ".join(invalid_dirs)
            + ". src/seeds/ debe ser plano: solo *.seed.ts. Migra los JSON "
              "de data/ a arrays/objetos locales dentro del seed que los usa, "
              "verifica referencias y elimina la carpeta solo cuando sea seguro."
        )
    return problems

def seed_root_relative(name):
    """Return the relative src/seeds directory for a tracked path, or None."""
    marker = "/src/seeds/"
    full = "/" + name
    if marker not in full:
        return None
    prefix = full.split(marker, 1)[0].lstrip("/")
    return (prefix + "/src/seeds").lstrip("/")

def validate_seed(path):
    """Enforce a single seed function, one table and no module-level extras."""
    s, errors = read(path)
    if errors:
        return errors
    from query_structure import tokens

    ts = tokens(s)
    # Even nested type/interface declarations must live in dedicated types/DTOs.
    for idx, (word, line) in enumerate(ts):
        if word == "type" and idx + 2 < len(ts) and ts[idx + 2][0] == "=":
            errors.append(
                f"Línea {line}: no declares aliases type dentro de .seed.ts; "
                "usa tipos importados o anotaciones directas."
            )
        if word == "interface" and idx + 2 < len(ts) and ts[idx + 2][0] in ("{", "<"):
            errors.append(
                f"Línea {line}: no declares interfaces dentro de .seed.ts; "
                "usa contratos importados."
            )
    n = len(ts)
    i = 0
    exported_functions = []

    def skip_import(index):
        j = index + 1
        nesting = 0
        seen_module = False
        while j < n:
            word, line = ts[j]
            if word in ("{", "(", "["):
                nesting += 1
            elif word in ("}", ")", "]"):
                nesting -= 1
            elif word == "STRING" and nesting == 0:
                seen_module = True
            if word == ";" and nesting == 0:
                return j + 1
            if seen_module and nesting == 0 and j + 1 < n:
                if ts[j + 1][1] > line and ts[j + 1][0] not in ("with", "assert"):
                    return j + 1
            j += 1
        return j

    while i < n:
        word, line = ts[i]
        if word == ";":
            i += 1
            continue
        if word == "import":
            i = skip_import(i)
            continue
        j = i
        if word == "export":
            j += 1
        if j < n and ts[j][0] == "async":
            j += 1
        if j < n and ts[j][0] == "function":
            fn = ts[j + 1][0] if j + 1 < n else ""
            if word != "export" or not re.fullmatch(r"seed[A-Z]\w*", fn):
                errors.append(
                    f"Línea {line}: exporta una única función seedNombre(...). "
                    "No se permiten funciones sueltas ni funciones sin exportar."
                )
            else:
                exported_functions.append(fn)
            # Move across arguments, optional type annotation and function body,
            # without mistaking braces in parameter types for the function body.
            k = j + 2
            paren = 0
            angle = 0
            saw_arguments = False
            body = None
            while k < n:
                value = ts[k][0]
                if value == "(":
                    paren += 1
                    saw_arguments = True
                elif value == ")":
                    paren = max(paren - 1, 0)
                elif value == "<" and paren == 0:
                    angle += 1
                elif value == ">" and paren == 0:
                    angle = max(0, angle - 1)
                elif value == "{" and paren == 0 and angle == 0 and saw_arguments:
                    body = k
                    break
                elif value == ";" and paren == 0 and saw_arguments:
                    break
                k += 1
            if body is None:
                errors.append(f"Línea {line}: función seed sin cuerpo válido.")
                i = max(k + 1, i + 1)
                continue
            k = body + 1
            depth = 1
            while k < n and depth:
                value = ts[k][0]
                if value == "{":
                    depth += 1
                elif value == "}":
                    depth -= 1
                k += 1
            if depth:
                errors.append(f"Línea {line}: llaves de la función seed desbalanceadas.")
            i = k
            continue
        errors.append(
            f"Línea {line}: declaración '{word}' fuera de la función seed. "
            "Solo se permiten imports y una única función exportada seedNombre(...). "
            "Mueve type/interface a otro archivo e importa sus tipos; "
            "incluye datos y constantes dentro de la función seed sin alterar resultados."
        )
        # Skip one statement to avoid reporting every identifier individually.
        i += 1
        depth = 0
        while i < n:
            v, current_line = ts[i]
            if v == ";" and depth == 0:
                i += 1
                break
            if depth == 0 and current_line > line and v in (
                "import", "export", "function", "async", "type",
                "interface", "enum", "class", "const", "let", "var",
            ):
                break
            if v in ("{", "(", "["):
                depth += 1
            elif v in ("}", ")", "]"):
                depth = max(0, depth - 1)
            i += 1
    if len(exported_functions) != 1:
        errors.append(
            "Cada .seed.ts necesita exactamente una función exportada "
            "seedNombre(...) (encontradas: "
            + str(len(exported_functions)) + ")."
        )
    imports = sorted(set(re.findall(r"\bfrom\s*['\"]([^'\"]+\.table)['\"]", s)))
    if len(imports) != 1:
        errors.append(
            f"Cada seed debe importar una sola tabla base (encontradas {len(imports)})."
        )
    if not re.search(r"\.\s*insert\s*\(", s):
        errors.append("Un seed debe insertar registros iniciales con Drizzle.")
    return errors
