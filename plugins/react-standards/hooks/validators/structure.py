"""Erixcel React hook validation; read-only."""
import re
from common.constants import FOLDERS

def validate_structure(root, changed):
    if not any(name.startswith("src/") for name in changed):
        return []
    issues = []
    for name in FOLDERS:
        if not (root / "src" / name).is_dir():
            issues.append("Falta la carpeta src/" + name + "/.")
    for file in ("src/main.tsx", "src/index.css"):
        if not (root / file).is_file():
            issues.append("Falta el archivo " + file + ".")
    # src is the home for code: do not put a nested .env file in the bundle.
    for name in changed:
        if re.search(r"(^|/)src/.*(?:^|/)\.env(?:\.example)?$", "/" + name):
            issues.append("No guardes archivos .env dentro de src/: " + name + ".")
    return issues
