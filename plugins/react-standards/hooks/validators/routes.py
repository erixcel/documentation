"""Reglas independientes para navegación React Router."""
import re
from common.discovery import changed_in


def validate_routes(root, changed):
    if not changed_in(changed, "routes"):
        return []
    base = root / "src/routes"
    errors = []

    # Regla 1: La carpeta de navegación src/routes debe existir.
    if not base.is_dir():
        return _validate_routes_directory(base)

    # Regla 2: React Router debe tener una definición de navegación TS/TSX.
    errors.extend(_validate_routes_navigation(base))

    # Regla 3: Las vistas de página no pertenecen a routes/.
    errors.extend(_validate_routes_page_locations(root, base))

    return errors


def _validate_routes_directory(base):
    if not base.is_dir():
        return ["src/routes/: falta carpeta de navegación."]
    return []


def _validate_routes_navigation(base):
    issues = []
    files = list(base.rglob("*.ts")) + list(base.rglob("*.tsx"))
    if not files:
        issues.append("src/routes/: configura rutas de React Router en archivos TS/TSX.")
    else:
        combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files)
        if not re.search(r"\b(createBrowserRouter|createHashRouter|RouteObject|Routes)\b", combined):
            issues.append("src/routes/: falta definición de navegación React Router.")
    return issues


def _validate_routes_page_locations(root, base):
    issues = []
    for path in base.rglob("*.tsx"):
        if path.name.endswith((".page.tsx", ".screen.tsx")):
            issues.append(f"{path.relative_to(root)}: las páginas deben estar bajo src/pages/, no en routes/.")
    return issues
