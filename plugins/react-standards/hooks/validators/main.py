"""Reglas independientes de arranque React para Erixcel."""
import re
from common.discovery import text


def validate_main(root, changed):
    if not ({"src/main.tsx", "src/index.css"} & changed):
        return []
    code = text(root, "src/main.tsx")
    errors = []

    # Regla 1: main.tsx debe crear la raíz de React con createRoot.
    errors.extend(_validate_main_root(code))

    # Regla 2: main.tsx debe utilizar RouterProvider.
    errors.extend(_validate_main_router(code))

    # Regla 3: main.tsx debe importar src/index.css.
    errors.extend(_validate_main_styles_import(code))
    return errors


def _validate_main_root(code):
    if not re.search(r"\bcreateRoot\s*\(", code):
        return ["src/main.tsx: falta createRoot(...) para montar la aplicación."]
    return []


def _validate_main_router(code):
    if not re.search(r"\bRouterProvider\b", code):
        return ["src/main.tsx: configura RouterProvider con el router exportado por src/routes."]
    return []


def _validate_main_styles_import(code):
    if not re.search(r"(?:import\s+['\"][^'\"]*index\.css['\"])", code):
        return ["src/main.tsx: importa src/index.css."]
    return []
