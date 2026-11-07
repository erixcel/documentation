"""Reglas independientes para Seeds de Erixcel NestJS."""
import re
from analyzers.query_structure import tokens
from validators._helpers import read


def validate_seed(path):
    source, errors = read(path)
    if errors:
        return errors
    ts = tokens(source)

    # Regla 1: No declarar aliases type ni interfaces dentro del Seed.
    errors.extend(_validate_seed_contracts(ts))

    # Regla 2: Solo imports y exactamente una función exportada seedNombre(...).
    errors.extend(_validate_seed_scope(ts))

    # Regla 3: Un Seed debe importar exactamente una tabla base.
    errors.extend(_validate_seed_single_table(source))

    # Regla 4: Un Seed debe insertar datos iniciales mediante Drizzle.
    errors.extend(_validate_seed_insert(source))

    return errors


def validate_seed_directory(folder):
    """Comprueba que la carpeta src/seeds sea plana y solo contenga *.seed.ts."""
    if not folder.is_dir():
        return []

    errors = []

    # Regla 5: src/seeds no admite archivos distintos de *.seed.ts.
    errors.extend(_validate_seed_directory_files(folder))

    # Regla 6: src/seeds no permite subcarpetas.
    errors.extend(_validate_seed_directory_subfolders(folder))

    return errors


def seed_root_relative(name):
    """Return the relative src/seeds directory for a tracked path, or None."""
    marker = "/src/seeds/"
    full = "/" + name
    if marker not in full:
        return None
    prefix = full.split(marker, 1)[0].lstrip("/")
    return (prefix + "/src/seeds").lstrip("/")


def _validate_seed_contracts(ts):
    errors = []
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
    return errors


def _validate_seed_scope(ts):
    errors = []
    n = len(ts)
    i = 0
    exported_functions = []

    while i < n:
        word, line = ts[i]
        if word == ";":
            i += 1
            continue
        if word == "import":
            i = _skip_seed_import(ts, i)
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
    return errors


def _skip_seed_import(ts, index):
    n = len(ts)
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



def _validate_seed_single_table(source):
    imports = sorted(set(re.findall(r"\bfrom\s*['\"]([^'\"]+\.table)['\"]", source)))
    if len(imports) != 1:
        return [f"Cada seed debe importar una sola tabla base (encontradas {len(imports)})."]
    return []


def _validate_seed_insert(source):
    if not re.search(r"\.\s*insert\s*\(", source):
        return ["Un seed debe insertar registros iniciales con Drizzle."]
    return []


def _validate_seed_directory_files(folder):
    invalid_files = sorted(
        entry.name for entry in folder.iterdir()
        if not entry.is_dir() and not (
            entry.is_file() and not entry.is_symlink()
            and entry.name.endswith(".seed.ts")
        )
    )
    if invalid_files:
        return [
            "Archivos no permitidos directamente en " + str(folder)
            + ": " + ", ".join(invalid_files)
            + ". Solo archivos *.seed.ts. Guarda los datos iniciales dentro "
              "de la función seed correspondiente."
        ]
    return []


def _validate_seed_directory_subfolders(folder):
    invalid_dirs = sorted(entry.name + "/" for entry in folder.iterdir() if entry.is_dir())
    if invalid_dirs:
        return [
            "Subcarpetas prohibidas dentro de " + str(folder)
            + ": " + ", ".join(invalid_dirs)
            + ". src/seeds/ debe ser plano: solo *.seed.ts. Migra los JSON "
              "de data/ a arrays/objetos locales dentro del seed que los usa, "
              "verifica referencias y elimina la carpeta solo cuando sea seguro."
        ]
    return []
