"""Reglas de la carpeta API generada en Erixcel React."""
from common.discovery import changed_in


def validate_api(root, changed):
    if not changed_in(changed, "api"):
        return []
    folder = root / "src/api"
    errors = []

    # Regla 1: Debe existir src/api/.
    if not folder.is_dir():
        return _validate_api_directory(folder)

    # Regla 2: Debe existir el cliente backend.api.ts generado.
    errors.extend(_validate_api_generated_client(folder))

    # Regla 3: No se permiten otros archivos dentro de src/api/.
    errors.extend(_validate_api_only_generated_client(folder))
    return errors


def _validate_api_directory(folder):
    if not folder.is_dir():
        return ["src/api/: falta carpeta API."]
    return []


def _validate_api_generated_client(folder):
    if not (folder / "backend.api.ts").is_file():
        return ["src/api/: falta backend.api.ts generado desde el backend."]
    return []


def _validate_api_only_generated_client(folder):
    errors = []
    for entry in sorted(folder.iterdir()):
        if entry.name != "backend.api.ts":
            errors.append(
                f"src/api/{entry.name}: solo se permite backend.api.ts generado; "
                "traslada clientes y sesiones a services/."
            )
    # El TS generado puede incluir clases, interfaces y tipos.
    return errors
