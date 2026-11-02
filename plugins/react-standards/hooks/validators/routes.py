"""Erixcel React hook validation; read-only."""
import re
from pathlib import Path
from common.discovery import changed_in

def validate_routes(root, changed):
    if not changed_in(changed, "routes"):
        return []
    base = root / "src/routes"
    if not base.is_dir():
        return ["src/routes/: falta carpeta de navegación."]
    issues = []
    files = list(base.rglob("*.ts")) + list(base.rglob("*.tsx"))
    if not files:
        issues.append("src/routes/: configura rutas de React Router en archivos TS/TSX.")
    else:
        combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files)
        if not re.search(r"\b(createBrowserRouter|createHashRouter|RouteObject|Routes)\b", combined):
            issues.append("src/routes/: falta definición de navegación React Router.")
    for path in base.rglob("*.tsx"):
        if path.name.endswith((".page.tsx", ".screen.tsx")):
            issues.append(f"{path.relative_to(root)}: las páginas deben estar bajo src/pages/, no en routes/.")
    return issues
