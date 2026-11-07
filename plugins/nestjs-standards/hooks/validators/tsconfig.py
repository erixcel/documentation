"""Validaciones de tsconfig/JSONC de Erixcel NestJS por reglas."""
import json
import re
from validators._helpers import read


def validate_tsconfig(path):
    source, errors = read(path)
    if errors:
        return errors

    # Regla 1: tsconfig.json debe ser JSON o JSONC válido.
    data, parse_errors = _validate_tsconfig_jsonc(source)
    if parse_errors:
        return parse_errors

    # Regla 2: compilerOptions debe existir y ser un objeto.
    options, options_errors = _validate_tsconfig_compiler_options(data)
    if options_errors:
        return options_errors

    # Regla 3: module y moduleResolution deben ser nodenext.
    errors.extend(_validate_tsconfig_module_resolution(options))

    # Regla 4: Los alias en paths deben ser listas de rutas.
    errors.extend(_validate_tsconfig_paths(options))

    return errors


def _validate_tsconfig_jsonc(source):
    # JSONC: eliminar comentarios sin descartar texto como URLs en strings.
    source = re.sub(r'''("(?:\\.|[^"\\])*")|//[^\n]*|/\*[\s\S]*?\*/''', lambda match: match.group(1) or "", source)
    source = re.sub(r",\s*(?=[}\]])", "", source)
    try:
        return json.loads(source), []
    except (ValueError, TypeError) as exc:
        return None, [f"tsconfig.json no es JSON/JSONC válido: {exc}"]


def _validate_tsconfig_compiler_options(data):
    options = data.get("compilerOptions") if isinstance(data, dict) else None
    if not isinstance(options, dict):
        return None, ["tsconfig.json requiere compilerOptions como objeto."]
    return options, []


def _validate_tsconfig_module_resolution(options):
    errors = []
    for key in ("module", "moduleResolution"):
        value = options.get(key)
        if isinstance(value, str) and value.lower() != "nodenext":
            errors.append(f"En esta convención NestJS, compilerOptions.{key} debe ser nodenext.")
    return errors


def _validate_tsconfig_paths(options):
    paths = options.get("paths")
    if paths is not None:
        if not isinstance(paths, dict) or not all(
            isinstance(value, list) and value and all(isinstance(item, str) for item in value)
            for value in paths.values()
        ):
            return ["compilerOptions.paths debe mapear alias a listas de rutas."]
    return []
