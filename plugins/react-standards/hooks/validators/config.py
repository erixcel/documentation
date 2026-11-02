"""Erixcel React hook validation; read-only."""
import json
import re
from common.discovery import text

def env_keys(s):
    found = {}
    for line in s.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if m:
            found[m.group(1)] = m.group(2).strip()
    return found

def validate_config(root, changed):
    if not ({".env", ".env.example", "package.json"} & changed):
        return []
    errors = []
    if "package.json" in changed:
        try:
            package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return ["package.json: JSON inválido."]
        if package.get("type") != "module":
            errors.append('package.json: configura "type": "module" para Vite.')
        for name in ("dev", "build", "lint", "preview", "test"):
            if not isinstance(package.get("scripts", {}).get(name), str):
                errors.append("package.json: falta el script " + name + ".")
        deps = package.get("dependencies") or {}
        dev = package.get("devDependencies") or {}
        for dep in ("react", "react-dom", "react-router-dom", "tailwindcss", "lucide-react", "@tailwindcss/vite"):
            if dep not in deps:
                errors.append("package.json: falta dependencia " + dep + ".")
        for dep in ("vite", "typescript", "eslint", "@vitejs/plugin-react"):
            if dep not in dev:
                errors.append("package.json: falta devDependency " + dep + ".")
    if ".env" in changed or ".env.example" in changed:
        if not (root / ".env.example").is_file():
            errors.append(".env.example: crea el inventario de variables del frontend.")
        else:
            sample = env_keys(text(root, ".env.example"))
            local = env_keys(text(root, ".env")) if (root / ".env").is_file() else {}
            for key in sorted(set(local) - set(sample)):
                errors.append(".env.example: documenta la variable " + key + " (sin copiar su valor).")
            for key in sorted(set(local) | set(sample)):
                if key.startswith("VITE_") and re.search(r"(TOKEN|SECRET|PASSWORD|PRIVATE_KEY|API_KEY)", key):
                    errors.append(key + ": las variables VITE_ son públicas; nunca expongas secretos.")
            for key, value in sample.items():
                if re.search(r"(?:sk_live_|ghp_|-----BEGIN PRIVATE KEY-----)", value):
                    errors.append(".env.example: elimina la credencial real del ejemplo en " + key + ".")
    return errors
