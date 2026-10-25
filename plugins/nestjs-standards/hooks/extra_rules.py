"""Static NestJS convention checks based on Erixcel documentation.

Heuristic, stdlib-only; no project writes, imports or execution.
"""
import json
import re
from pathlib import Path
from query_structure import tokens

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
        if depth == 1 and word == "(" and i > 0 and IDENT.fullmatch(t[i - 1][0]):
            method = t[i - 1][0]
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


def validate_controller(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".controller.ts", "Controller", "Controller")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith(("@db/", "@queries/")) or "drizzle-orm" in p for p in imports):
        errors.append("Un Controller no debe importar Drizzle, tablas ni Queries; delega al Service.")
    methods = class_methods(s)
    errors += controller_dto_files(path, s)
    routes = {"Get", "Post", "Put", "Patch", "Delete", "Options", "Head", "All"}
    for method, decorators, body, line in methods:
        if not (routes & set(decorators)):
            continue
        label = f"Línea {line} ({method})"
        if "ApiOperation" not in decorators:
            errors.append(f"{label}: falta @ApiOperation.")
        if decorators.count("ApiResponse") < 2:
            errors.append(f"{label}: requiere @ApiResponse exitoso y de error.")
        if "TraceNode" not in decorators or decorators[-1] != "TraceNode":
            errors.append(f"{label}: @TraceNode debe estar al final de los decoradores.")
        if decorators and decorators[0] not in routes:
            errors.append(f"{label}: el decorador HTTP debe ser el primero del endpoint.")
        if body[:2] != ["return", "this"] or not re.search(
            r"\breturn\s+this\s*\.\s*\w*[Ss]ervice\s*\.\s*\w+\s*\(", " ".join(body)
        ):
            errors.append(f"{label}: delega directamente con return this.nombreService.metodo(...).")
        if any(x in body for x in ("const", "let", "if", "try", "while", "for", "throw")):
            errors.append(f"{label}: el Controller no debe contener lógica de negocio.")
    return errors


def validate_service(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".service.ts", "Service", "Injectable")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith("@db/") or "drizzle-orm" in p for p in imports):
        errors.append("El Service debe acceder a datos mediante Queries, no mediante Drizzle o tablas.")
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", s):
        errors.append("El Service no debe ejecutar consultas Drizzle directamente.")
    if re.search(r"@(?:Controller|Get|Post|Patch|Delete)\s*\(", s):
        errors.append("Las rutas HTTP corresponden al Controller, no al Service.")
    return errors


def validate_module(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".module.ts", "Module", "Module")
    if not re.search(r"@Module\s*\(\s*\{", s):
        errors.append("@Module debe registrar las dependencias mediante un objeto.")
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", s):
        errors.append("No coloques consultas de datos dentro de un módulo.")
    return errors


def validate_dto(path):
    s, errors = read(path)
    if errors:
        return errors
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.dto\.ts", path.name):
        errors.append("Nombre de DTO: kebab-case y sufijo .dto.ts.")
    names = class_names(s)
    if not names:
        errors.append("El DTO debe declarar una o más clases.")
    for name in names:
        if not name.endswith("Dto"):
            errors.append(f"La clase {name} debe terminar en Dto.")
    traces = len(re.findall(r"@Trace\s*\(\s*\{[^}]*\btype\s*:\s*['\"]validation['\"]", s, re.S))
    if names and traces < len(names):
        errors.append("Cada clase DTO debe llevar @Trace({ type: 'validation' }).")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith(("@queries/", "@db/connection", "@db/config")) for p in imports):
        errors.append("Los DTO no deben consultar la base de datos ni depender de su conexión.")
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", s):
        errors.append("Las consultas no pertenecen a los DTO.")
    return errors


def validate_function(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".function.ts", "Function")
    if not re.search(r"\bstatic\s+(?:async\s+)?[A-Za-z_$]\w*\s*(?:<[^>]+>)?\s*\(", s):
        errors.append("Las utilidades de .function.ts deben exponerse como métodos static.")
    if re.search(r"@(?:Controller|Get|Post|Module|Injectable)\s*\(", s):
        errors.append("Una Function no debe declarar endpoints ni registrar providers NestJS.")
    imports = re.findall(r"\bfrom\s*['\"]([^'\"]+)['\"]", s)
    if any(p.startswith(("@db/tables/", "@db/connection")) for p in imports):
        errors.append("Las Functions no deben consultar tablas: usa la capa Queries.")
    return errors


def validate_table(path):
    s, errors = read(path)
    if errors:
        return errors
    count = len(re.findall(r"\bpgTable\s*\(", s))
    if count != 1:
        errors.append(f"Un archivo .table.ts define exactamente una tabla pgTable (encontradas {count}).")
    fields = {
        "createdAt": ("created_at", True),
        "updatedAt": ("updated_at", True),
        "deletedAt": ("deleted_at", False),
    }
    for field, (column, required) in fields.items():
        regex = r"\b" + field + r"\s*:\s*timestamp\s*\(\s*['\"]" + column + r"['\"]\s*\)"
        match = re.search(regex, s)
        if not match:
            errors.append(f"Falta {field}: timestamp('{column}') en inglés.")
        elif required and not re.match(r"\s*\.defaultNow\s*\(\s*\)\s*\.notNull\s*\(\s*\)", s[match.end():]):
            errors.append(f"{field} requiere .defaultNow().notNull().")
    if not re.search(r"\bexport\s+const\s+\w+\s*=\s*pgTable\s*\(", s):
        errors.append("Exporta la definición principal con export const ... = pgTable(...).")
    for name in ("$inferSelect", "$inferInsert"):
        if name not in s:
            errors.append(f"Exporta un tipo Drizzle basado en {name}.")
    return errors


def validate_seed(path):
    s, errors = read(path)
    if errors:
        return errors
    if not re.search(r"\bexport\s+(?:async\s+)?function\s+seed[A-Z]\w*\s*\(", s):
        errors.append("Exporta una función seedNombre(...) por archivo.")
    imports = sorted(set(re.findall(r"\bfrom\s*['\"]([^'\"]+\.table)['\"]", s)))
    if len(imports) != 1:
        errors.append(f"Cada seed debe importar una sola tabla base (encontradas {len(imports)}).")
    if ".insert(" not in s and not re.search(r"\.\s*insert\s*\(", s):
        errors.append("Un seed debe insertar registros iniciales con Drizzle.")
    return errors


def validate_script(path):
    s, errors = read(path)
    if errors:
        return errors
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.ts", path.name):
        errors.append("Los scripts usan nombres descriptivos kebab-case terminados en .ts.")
    if re.search(r"(?i)\b(?:password|api_?key|secret|access_?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", s):
        errors.append("Posible credencial incrustada en script: usa variables de entorno.")
    if re.search(r"['\"]/(?:Users|home)/[^'\"]+['\"]", s):
        errors.append("No uses rutas absolutas de otra máquina: resuélvelas desde el proyecto.")
    return errors


def validate_tsconfig(path):
    s, errors = read(path)
    if errors:
        return errors
    # JSONC: remove comments without discarding URL-looking text in strings.
    s = re.sub(r"""("(?:\\.|[^"\\])*")|//[^\n]*|/\*[\s\S]*?\*/""", lambda m: m.group(1) or "", s)
    s = re.sub(r",\s*(?=[}\]])", "", s)
    try:
        data = json.loads(s)
    except (ValueError, TypeError) as exc:
        return [f"tsconfig.json no es JSON/JSONC válido: {exc}"]
    opts = data.get("compilerOptions") if isinstance(data, dict) else None
    if not isinstance(opts, dict):
        return ["tsconfig.json requiere compilerOptions como objeto."]
    for key in ("module", "moduleResolution"):
        value = opts.get(key)
        if isinstance(value, str) and value.lower() != "nodenext":
            errors.append(f"En esta convención NestJS, compilerOptions.{key} debe ser nodenext.")
    paths = opts.get("paths")
    if paths is not None:
        if not isinstance(paths, dict) or not all(
            isinstance(v, list) and v and all(isinstance(x, str) for x in v)
            for v in paths.values()
        ):
            errors.append("compilerOptions.paths debe mapear alias a listas de rutas.")
    return errors
