"""Reglas de estructura global para proyectos Erixcel React."""
import re
from common.constants import FOLDERS


def validate_structure(root, changed):
    if not any(name.startswith("src/") for name in changed):
        return []
    errors = []

    # Regla 1: Las carpetas base de src/ deben existir.
    errors.extend(_validate_structure_folders(root))

    # Regla 2: Los archivos main.tsx e index.css deben existir.
    errors.extend(_validate_structure_entrypoints(root))

    # Regla 3: No se permiten archivos .env dentro de src/.
    errors.extend(_validate_structure_no_nested_env(changed))
    return errors


def _validate_structure_folders(root):
    issues = []
    for name in FOLDERS:
        if not (root / "src" / name).is_dir():
            issues.append("Falta la carpeta src/" + name + "/.")
    return issues


def _validate_structure_entrypoints(root):
    issues = []
    for file in ("src/main.tsx", "src/index.css"):
        if not (root / file).is_file():
            issues.append("Falta el archivo " + file + ".")
    return issues


def _validate_structure_no_nested_env(changed):
    issues = []
    for name in changed:
        if re.search(r"(^|/)src/.*(?:^|/)\.env(?:\.example)?$", "/" + name):
            issues.append("No guardes archivos .env dentro de src/: " + name + ".")
    return issues
