"""Erixcel React hook validation; read-only."""
from common.discovery import changed_in

def validate_api(root, changed):
    if not changed_in(changed, "api"):
        return []
    folder = root / "src/api"
    if not folder.is_dir():
        return ["src/api/: falta carpeta API."]
    issues = []
    expected = folder / "backend.api.ts"
    if not expected.is_file():
        issues.append("src/api/: falta backend.api.ts generado desde el backend.")
    for entry in sorted(folder.iterdir()):
        if entry.name != "backend.api.ts":
            issues.append(f"src/api/{entry.name}: solo se permite backend.api.ts generado; "
                          "traslada clientes y sesiones a services/.")
    # No content lint: generated TypeScript may use classes/interfaces/types.
    return issues
