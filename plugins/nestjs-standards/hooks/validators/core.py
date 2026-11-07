"""Reglas independientes para src/core/*.core.ts de NestJS."""
import re
from pathlib import Path


# Erixcel's published naming intentionally uses TraceFlow, not Traceflow.
SPECIAL_NAMES = {"traceflow": "TraceFlow"}
FUNCTION_RE = re.compile(r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")
EXPORTED_RE = re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)", re.S)
BAD_BOOTSTRAP_RE = re.compile(r"\bNestFactory\b|\bapp\s*\.\s*listen\s*\(|@\s*(?:Controller|Get|Post|Patch|Put|Delete)\b")
IMPORT_RE = re.compile(r"\bimport\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]", re.S)


def validate_core(path):
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"No se pudo leer: {exc}"]

    code = mask_comments_and_strings(source)
    errors = []
    declared = FUNCTION_RE.findall(code)
    exported = EXPORTED_RE.findall(code)

    # Regla 1: El archivo core debe usar kebab-case y terminar en .core.ts.
    errors.extend(_validate_core_filename(path))

    # Regla 2: Exactamente una función debe estar declarada y exportada.
    errors.extend(_validate_core_function_count(declared, exported))

    # Regla 3: La función debe tener nombre setupNombre y recibir INestApplication.
    if len(declared) == 1 and len(exported) == 1:
        errors.extend(_validate_core_function_signature(path, exported[0]))

    # Regla 4: Un core no debe iniciar NestFactory ni registrar endpoints.
    errors.extend(_validate_core_no_bootstrap(code))

    # Regla 5: Debe existir src/main.ts y poder leerse.
    main_text, main_errors = _validate_core_main_readable(path)
    errors.extend(main_errors)
    if main_errors:
        return errors

    # Regla 6: main.ts debe importar setupNombre desde su archivo core.
    errors.extend(_validate_core_main_import(path, main_text))

    # Regla 7: main.ts debe ejecutar setupNombre(app) entre create() y listen().
    errors.extend(_validate_core_main_invocation(path, main_text))

    return errors


def _validate_core_filename(path):
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.core\.ts", path.name):
        return ["El nombre debe usar kebab-case y terminar en .core.ts."]
    return []


def _validate_core_function_count(declared, exported):
    if len(declared) != 1 or len(exported) != 1:
        return [
            "Debe haber exactamente una función declarada y exportada; "
            f"encontradas {len(declared)} declaraciones y {len(exported)} exportaciones."
        ]
    return []


def _validate_core_function_signature(path, exported):
    fn, params = exported
    expected = expected_name(path)
    errors = []
    if fn != expected:
        errors.append(f"La función exportada debe llamarse {expected}, no {fn}.")
    if not re.fullmatch(r"\s*app\s*:\s*INestApplication\s*", params):
        errors.append("La función debe recibir solo (app: INestApplication).")
    return errors


def _validate_core_no_bootstrap(code):
    if BAD_BOOTSTRAP_RE.search(code):
        return ["No inicies NestFactory, app.listen ni declares rutas HTTP en archivos core."]
    return []


def _validate_core_main_readable(path):
    main = path.parent.parent / "main.ts"
    if not main.exists():
        return None, ["No se encontró src/main.ts para verificar la integración del core."]
    try:
        return main.read_text(encoding="utf-8"), []
    except (OSError, UnicodeError) as exc:
        return None, [f"No se pudo leer main.ts: {exc}"]


def _validate_core_main_import(path, main_text):
    imported = any(
        expected_name(path) in [part.strip() for part in bindings.replace("\n", " ").split(",")]
        and route.endswith("/" + path.name[:-3])
        for bindings, route in IMPORT_RE.findall(main_text)
    )
    if not imported:
        return [f"src/main.ts debe importar {expected_name(path)} desde el archivo core."]
    return []


def _validate_core_main_invocation(path, main_text):
    main_code = mask_comments_and_strings(main_text)
    invocation = re.search(r"\b" + re.escape(expected_name(path)) + r"\s*\(\s*app\s*\)", main_code)
    created = re.search(r"\bNestFactory\s*\.\s*create\s*\(", main_code)
    listened = re.search(r"\bapp\s*\.\s*listen\s*\(", main_code)
    if not invocation:
        return [f"src/main.ts debe ejecutar {expected_name(path)}(app)."]
    if not created or not listened or not created.start() < invocation.start() < listened.start():
        return [f"{expected_name(path)}(app) debe ejecutarse después de NestFactory.create y antes de app.listen."]
    return []


def mask_comments_and_strings(code):
    """Preserve offsets and newlines while masking common TS comments/strings."""
    out = list(code)
    token = re.compile(r"//[^\n]*|/\*[\s\S]*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|\x60(?:\\.|[^\x60\\])*\x60", re.S)
    for match in token.finditer(code):
        for i in range(match.start(), match.end()):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def expected_name(path):
    stem = path.name[:-len(".core.ts")]
    parts = re.split(r"[-_]", stem)
    return "setup" + "".join(SPECIAL_NAMES.get(p.lower(), p[:1].upper() + p[1:]) for p in parts if p)


