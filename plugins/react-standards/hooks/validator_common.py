#!/usr/bin/env python3
"""Independent, read-only Codex lifecycle validators for React + Vite.

No external modules, no shell execution, and no file modifications.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

STATE = Path.home() / ".codex" / "erixcel-react-validator"
SKIP = {".git", ".codex", ".vercel", "node_modules", "dist", "build", "coverage", ".next", ".turbo"}
FOLDERS = ("api", "assets", "components", "hooks", "modules", "routes", "services")
DESCRIPTIONS = {
    "structure": "desarrollo/react/estructura",
    "main": "desarrollo/react/src/main",
    "components": "desarrollo/react/src/components",
    "hooks": "desarrollo/react/src/hooks",
    "routes": "desarrollo/react/src/routes",
    "modules": "desarrollo/react/src/modules",
    "api-services": "desarrollo/react/src/services",
    "config": "desarrollo/react/package-json",
}


def project_for(payload):
    cwd = payload.get("cwd")
    if not isinstance(cwd, str):
        return None
    here = Path(cwd).resolve()
    if not here.is_dir():
        return None
    candidates = [here, here / "frontend"]
    candidates += [parent for parent in here.parents if parent != Path(parent.anchor)]
    for candidate in candidates:
        if looks_like_react(candidate):
            return candidate
    for base, dirs, files in os.walk(here):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        path = Path(base)
        if path != here and len(path.relative_to(here).parts) > 3:
            dirs[:] = []
            continue
        if looks_like_react(path):
            return path
    return None


def looks_like_react(root):
    package = root / "package.json"
    if not package.is_file() or not (root / "src/main.tsx").is_file():
        return False
    try:
        cfg = json.loads(package.read_text(encoding="utf-8"))
        libs = {**cfg.get("dependencies", {}), **cfg.get("devDependencies", {})}
        return "react" in libs and "vite" in libs
    except (OSError, ValueError, TypeError):
        return False


def snapshot_id(payload, root):
    turn = str(payload.get("session_id") or payload.get("conversation_id") or "local")
    return hashlib.sha256((str(root) + "::" + turn).encode()).hexdigest()[:32]


def discover(root):
    result = {}
    for name in ("package.json", ".env", ".env.example"):
        file = root / name
        if file.is_file():
            result[name] = file
    src = root / "src"
    if src.is_dir():
        result["src/"] = src
        for parent, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in SKIP)
            base = Path(parent)
            if base != src:
                result[base.relative_to(root).as_posix() + "/"] = base
            for file in files:
                path = base / file
                if not path.is_symlink() and path.is_file():
                    result[path.relative_to(root).as_posix()] = path
    return result


def fingerprint(path):
    try:
        if path.is_dir():
            return "<directory>"
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2", ".mp4", ".gif"}:
            s = path.stat()
            return str(s.st_size) + ":" + str(s.st_mtime_ns)
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "<unreadable>"


def snapshot(root):
    return {name: fingerprint(path) for name, path in discover(root).items()}


def store(payload, root):
    STATE.mkdir(parents=True, exist_ok=True)
    state = STATE / (snapshot_id(payload, root) + ".json")
    data = {"root": str(root), "files": snapshot(root)}
    # No file contents, especially no .env values, are stored.
    temp = state.with_suffix(".tmp")
    temp.write_text(json.dumps(data), encoding="utf-8")
    temp.replace(state)


def load(payload, root):
    state = STATE / (snapshot_id(payload, root) + ".json")
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
        return data.get("files") if data.get("root") == str(root) else None
    except (OSError, ValueError, TypeError):
        return None


def text(root, name):
    try:
        return (root / name).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


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


def validate_components(root, changed):
    errors = []
    for name in changed:
        if not name.startswith("src/components/") or name.endswith("/"):
            continue
        path = root / name
        if not path.exists():
            continue
        if path.suffix not in (".tsx", ".ts", ".css", ".svg", ".json"):
            continue
        if path.suffix == ".tsx" and re.search(r"\b(?:fetch|axios)\s*\(", text(root, name)):
            errors.append(name + ": mueve las llamadas HTTP directas a src/api o src/services.")
    return errors


def validate_hooks(root, changed):
    errors = []
    for name in changed:
        if not name.startswith("src/hooks/") or not name.endswith((".ts", ".tsx")):
            continue
        s = text(root, name)
        if re.search(r"\b(?:function|const)\s+use[A-Z]\w*", s):
            continue
        errors.append(name + ": el hook personalizado debe declarar una función useXxx.")
    return errors


def validate_routes(root, changed):
    if not any(name.startswith("src/routes/") for name in changed):
        return []
    files = list((root / "src/routes").rglob("*.ts")) + list((root / "src/routes").rglob("*.tsx"))
    if not files:
        return ["src/routes/: define al menos un archivo TS/TSX de configuración de rutas."]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files)
    if not re.search(r"\b(createBrowserRouter|createHashRouter|RouteObject|Routes)\b", combined):
        return ["src/routes/: organiza la definición de rutas para React Router (createBrowserRouter, createHashRouter o Routes)."]
    return []


def validate_modules(root, changed):
    if not any(name.startswith("src/modules/") for name in changed):
        return []
    base = root / "src/modules"
    if not base.is_dir():
        return []
    root_files = [entry.name for entry in base.iterdir() if entry.is_file() and entry.name != ".gitkeep"]
    if root_files:
        return ["src/modules/: agrupa funcionalidades en carpetas por dominio, no en archivos sueltos: " + ", ".join(sorted(root_files))]
    return []


def validate_api_services(root, changed):
    errors = []
    for name in changed:
        if not (name.startswith("src/api/") or name.startswith("src/services/")):
            continue
        if not name.endswith((".ts", ".tsx")) or not (root / name).is_file():
            continue
        data = text(root, name)
        if re.search(r"""\bfrom\s+['"]react-dom(?:/client)?['"]""", data):
            errors.append(name + ": la capa API/Services no debe montar componentes con react-dom.")
        if re.search(r"\bprocess\.env\b", data):
            errors.append(name + ": con Vite utiliza import.meta.env, no process.env.")
    return errors


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


CHECKS = {
    "structure": validate_structure,
    "main": validate_main,
    "components": validate_components,
    "hooks": validate_hooks,
    "routes": validate_routes,
    "modules": validate_modules,
    "api-services": validate_api_services,
    "config": validate_config,
}


def stop(payload, kind):
    if payload.get("hook_event_name") != "Stop":
        return {}
    root = project_for(payload)
    if root is None:
        return {}
    before = load(payload, root)
    if before is None:
        return {"systemMessage": "Erixcel React: no existe snapshot inicial para este turno; se omite validación."}
    after = snapshot(root)
    changed = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
    errors = CHECKS[kind](root, changed)
    if not errors:
        return {}
    doc = "https://docs.erixcel.com/" + DESCRIPTIONS[kind]
    reason = ("Erixcel React / " + kind + ": errores detectados tras editar el frontend:\n"
              + "\n".join("- " + issue for issue in errors[:20])
              + "\nConvenciones: " + doc
              + "\nCorrige lo indicado, sin alterar el comportamiento, y vuelve a comprobarlo.")
    if payload.get("stop_hook_active"):
        return {"systemMessage": reason + "\nNo se bloquea otra vez para evitar bucles."}
    return {"decision": "block", "reason": reason}


def run(kind):
    if len(sys.argv) >= 3 and sys.argv[1] == "--check":
        root = Path(sys.argv[2]).resolve()
        if not looks_like_react(root):
            print("Erixcel React: no es un proyecto React + Vite reconocido.")
            return 2
        result = CHECKS[kind](root, set(snapshot(root).keys()))
        if result:
            print("\n".join("- " + item for item in result))
            return 1
        print("Erixcel React " + kind + ": OK")
        return 0
    try:
        payload = json.load(sys.stdin)
        print(json.dumps(stop(payload, kind), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"systemMessage": "Erixcel React: validación incompleta (" + type(exc).__name__ + ")."}))
    return 0
