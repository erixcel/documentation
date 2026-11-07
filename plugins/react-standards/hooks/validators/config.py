"""Reglas de configuración de paquete y variables de entorno para React."""
import json
import re
from common.discovery import text


def validate_config(root, changed):
    if not ({".env", ".env.example", "package.json"} & changed):
        return []
    errors = []

    if "package.json" in changed:
        # Regla 1: package.json debe contener JSON válido.
        package, parse_errors = _validate_config_package_json(root)
        if parse_errors:
            return parse_errors

        # Regla 2: Vite requiere "type": "module".
        errors.extend(_validate_config_module_type(package))

        # Regla 3: El paquete debe proporcionar los scripts habituales.
        errors.extend(_validate_config_scripts(package))

        # Regla 4: Las dependencias de ejecución deben estar declaradas.
        errors.extend(_validate_config_dependencies(package))

        # Regla 5: Las herramientas deben figurar en devDependencies.
        errors.extend(_validate_config_dev_dependencies(package))

    if ".env" in changed or ".env.example" in changed:
        # Regla 6: Debe existir .env.example.
        if not (root / ".env.example").is_file():
            errors.extend(_validate_config_env_example(root))
        else:
            sample = env_keys(text(root, ".env.example"))
            local = env_keys(text(root, ".env")) if (root / ".env").is_file() else {}

            # Regla 7: .env.example debe inventariar todas las variables.
            errors.extend(_validate_config_env_inventory(sample, local))

            # Regla 8: Nunca colocar secretos en variables VITE_.
            errors.extend(_validate_config_public_env_secrets(sample, local))

            # Regla 9: .env.example no debe incluir credenciales reales.
            errors.extend(_validate_config_example_credentials(sample))

    return errors


def _validate_config_package_json(root):
    try:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None, ["package.json: JSON inválido."]
    return package, []


def _validate_config_module_type(package):
    if package.get("type") != "module":
        return ['package.json: configura "type": "module" para Vite.']
    return []


def _validate_config_scripts(package):
    errors = []
    for name in ("dev", "build", "lint", "preview", "test"):
        if not isinstance(package.get("scripts", {}).get(name), str):
            errors.append("package.json: falta el script " + name + ".")
    return errors


def _validate_config_dependencies(package):
    errors = []
    deps = package.get("dependencies") or {}
    for dep in ("react", "react-dom", "react-router-dom", "tailwindcss", "lucide-react", "@tailwindcss/vite"):
        if dep not in deps:
            errors.append("package.json: falta dependencia " + dep + ".")
    return errors


def _validate_config_dev_dependencies(package):
    errors = []
    dev = package.get("devDependencies") or {}
    for dep in ("vite", "typescript", "eslint", "@vitejs/plugin-react"):
        if dep not in dev:
            errors.append("package.json: falta devDependency " + dep + ".")
    return errors


def _validate_config_env_example(root):
    if not (root / ".env.example").is_file():
        return [".env.example: crea el inventario de variables del frontend."]
    return []


def _validate_config_env_inventory(sample, local):
    errors = []
    for key in sorted(set(local) - set(sample)):
        errors.append(".env.example: documenta la variable " + key + " (sin copiar su valor).")
    return errors


def _validate_config_public_env_secrets(sample, local):
    errors = []
    for key in sorted(set(local) | set(sample)):
        if key.startswith("VITE_") and re.search(r"(TOKEN|SECRET|PASSWORD|PRIVATE_KEY|API_KEY)", key):
            errors.append(key + ": las variables VITE_ son públicas; nunca expongas secretos.")
    return errors


def _validate_config_example_credentials(sample):
    errors = []
    for key, value in sample.items():
        if re.search(r"(?:sk_live_|ghp_|-----BEGIN PRIVATE KEY-----)", value):
            errors.append(".env.example: elimina la credencial real del ejemplo en " + key + ".")
    return errors


def env_keys(source):
    """Extrae pares de .env sin leer su contenido como JavaScript."""
    found = {}
    for line in source.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if match:
            found[match.group(1)] = match.group(2).strip()
    return found
