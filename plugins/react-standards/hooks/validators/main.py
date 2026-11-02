"""Erixcel React hook validation; read-only."""
import re
from common.discovery import text

def validate_main(root, changed):
    if not ({"src/main.tsx", "src/index.css"} & changed):
        return []
    code = text(root, "src/main.tsx")
    errors = []
    if not re.search(r"\bcreateRoot\s*\(", code):
        errors.append("src/main.tsx: falta createRoot(...) para montar la aplicación.")
    if not re.search(r"\bRouterProvider\b", code):
        errors.append("src/main.tsx: configura RouterProvider con el router exportado por src/routes.")
    if not re.search(r"""(?:import\s+['"][^'"]*index\.css['"])""", code):
        errors.append("src/main.tsx: importa src/index.css.")
    return errors
