"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

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
