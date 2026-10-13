"""Validate Erixcel src/core/*.core.ts conventions; read-only static checks."""
import re
from pathlib import Path

# Erixcel's published naming intentionally uses TraceFlow, not Traceflow.
SPECIAL_NAMES = {"traceflow": "TraceFlow"}
FUNCTION_RE = re.compile(r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")
EXPORTED_RE = re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)", re.S)
BAD_BOOTSTRAP_RE = re.compile(r"\bNestFactory\b|\bapp\s*\.\s*listen\s*\(|@\s*(?:Controller|Get|Post|Patch|Put|Delete)\b")
IMPORT_RE = re.compile(r"\bimport\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]", re.S)


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


def validate_core(path):
    """Returns violations; not a TypeScript parser or runtime test."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"No se pudo leer: {exc}"]
    code = mask_comments_and_strings(source)
    errors = []
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.core\.ts", path.name):
        errors.append("El nombre debe usar kebab-case y terminar en .core.ts.")
    names = FUNCTION_RE.findall(code)
    exported = EXPORTED_RE.findall(code)
    if len(names) != 1 or len(exported) != 1:
        errors.append(f"Debe haber exactamente una función declarada y exportada; encontradas {len(names)} declaraciones y {len(exported)} exportaciones.")
    else:
        expected = expected_name(path)
        fn, params = exported[0]
        if fn != expected:
            errors.append(f"La función exportada debe llamarse {expected}, no {fn}.")
        if not re.fullmatch(r"\s*app\s*:\s*INestApplication\s*", params):
            errors.append("La función debe recibir solo (app: INestApplication).")
    if BAD_BOOTSTRAP_RE.search(code):
        errors.append("No inicies NestFactory, app.listen ni declares rutas HTTP en archivos core.")

    main = path.parent.parent / "main.ts"
    if not main.exists():
        errors.append("No se encontró src/main.ts para verificar la integración del core.")
        return errors
    try:
        main_text = main.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return errors + [f"No se pudo leer main.ts: {exc}"]
    imported = any(
        expected_name(path) in [part.strip() for part in bindings.replace("\n", " ").split(",")]
        and route.endswith("/" + path.name[:-3])
        for bindings, route in IMPORT_RE.findall(main_text)
    )
    if not imported:
        errors.append(f"src/main.ts debe importar {expected_name(path)} desde el archivo core.")
    main_code = mask_comments_and_strings(main_text)
    invocation = re.search(r"\b" + re.escape(expected_name(path)) + r"\s*\(\s*app\s*\)", main_code)
    created = re.search(r"\bNestFactory\s*\.\s*create\s*\(", main_code)
    listened = re.search(r"\bapp\s*\.\s*listen\s*\(", main_code)
    if not invocation:
        errors.append(f"src/main.ts debe ejecutar {expected_name(path)}(app).")
    elif (not created or not listened or not created.start() < invocation.start() < listened.start()):
        errors.append(f"{expected_name(path)}(app) debe ejecutarse después de NestFactory.create y antes de app.listen.")
    return errors
