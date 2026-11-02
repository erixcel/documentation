#!/usr/bin/env python3
"""Independent, read-only Codex lifecycle validators for React + Vite.

No external modules, no shell execution, and no file modifications.
"""
import hashlib
import json
import os
import re
import sys
import subprocess
from pathlib import Path

STATE = Path.home() / ".codex" / "erixcel-react-validator"
SKIP = {".git", ".codex", ".vercel", "node_modules", "dist", "build", "coverage", ".next", ".turbo"}
FOLDERS = ("api", "assets", "components", "hooks", "modules", "routes", "services")
DESCRIPTIONS = {
    "structure": "desarrollo/react/estructura",
    "main": "desarrollo/react/src/main",
    "styles": "desarrollo/react/src/styles",
    "api": "desarrollo/react/src/api",
    "components": "desarrollo/react/src/components",
    "hooks": "desarrollo/react/src/hooks",
    "services": "desarrollo/react/src/services",
    "module-routes": "desarrollo/react/src/modules",
    "package": "desarrollo/react/package-json",
    "env": "desarrollo/react/env",
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
    if not package.is_file() or not (root / "src").is_dir():
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


def changed_in(changed, segment):
    return any(name.startswith("src/" + segment + "/")
               or ("/" + segment + "/") in name
               for name in changed)


def ast_check(root, kind, paths):
    """TypeScript AST analysis via local TypeScript dependency; never modify files."""
    files = sorted(set(paths))
    if not files:
        return []
    script = Path(__file__).with_name("validate-ast.mjs")
    try:
        result = subprocess.run(
            ["node", str(script), str(root), kind, *files],
            capture_output=True, text=True, timeout=25, check=False,
        )
        if result.returncode != 0:
            return [f"TypeScript AST: no se pudo completar el análisis de {kind}. "
                    "Comprueba Node.js y la instalación npm del frontend."]
        issues = json.loads(result.stdout)
        return [f"{err['file']}:{err['line']}: {err['rule']}" for err in issues]
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return ["TypeScript AST: fallo al analizar. Instala las dependencias y "
                "comprueba que Node.js/TypeScript estén disponibles."]


def validate_styles(root, changed):
    issues = []
    style_changes = any(name.startswith("src/") and name.endswith((".css", ".scss", ".sass", ".less")) for name in changed)
    tsx_changes = [n for n in changed if n.startswith("src/") and n.endswith(".tsx") and (root / n).is_file()]
    if not style_changes and not tsx_changes:
        return issues
    forbidden = (".css", ".scss", ".sass", ".less")
    # Validate all current style files after an edit of any style file/directory.
    for path in (root / "src").rglob("*"):
        if not path.is_file() or path.is_symlink() or any(p in SKIP for p in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.endswith(forbidden) and rel != "src/index.css":
            issues.append(f"{rel}: CSS propio prohibido; utiliza className con Tailwind en lugar de CSS externo.")
    css = root / "src/index.css"
    if style_changes and css.is_file():
        data = css.read_text(encoding="utf-8")
        # Allow optional comments, one import and @theme blocks with tokens only.
        cleaned = re.sub(r"/\*[\s\S]*?\*/", "", data).strip()
        imp = re.match(r"""@import\s+['"]tailwindcss['"]\s*;""", cleaned)
        if not imp:
            issues.append("src/index.css:1: el archivo debe comenzar con @import 'tailwindcss';.")
        else:
            rest = cleaned[imp.end():].strip()
            while rest:
                match = re.match(r"@theme(?:\s+(?:inline|static|default))?\s*\{", rest)
                if not match:
                    issues.append("src/index.css: solo se permiten @import 'tailwindcss'; y bloques @theme. "
                                  "Prohibidos selectores, @apply, @layer, @media y @keyframes.")
                    break
                depth = 1
                end = match.end()
                while end < len(rest) and depth:
                    if rest[end] == "{":
                        depth += 1
                    elif rest[end] == "}":
                        depth -= 1
                    end += 1
                if depth:
                    issues.append("src/index.css: bloque @theme sin cierre.")
                    break
                body = rest[match.end():end - 1].strip()
                tokens = re.findall(r"--[A-Za-z0-9_-]+\s*:\s*[^;{}]+;", body)
                if re.sub(r"--[A-Za-z0-9_-]+\s*:\s*[^;{}]+;", "", body).strip():
                    issues.append("src/index.css: @theme solo puede contener tokens CSS (--nombre: valor;).")
                rest = rest[end:].strip()
    issues += ast_check(root, "styles", tsx_changes)
    return issues


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


def validate_components(root, changed):
    if not changed_in(changed, "components"):
        return []
    issues = []
    base = root / "src/components"
    if not base.is_dir():
        return ["src/components/: falta carpeta components."]
    for entry in sorted(base.iterdir()):
        if entry.name not in ("simple", "complex") or not entry.is_dir():
            issues.append(f"src/components/{entry.name}: en la raíz solo existen simple/ y complex/.")
    for folder in ("simple", "complex"):
        if not (base / folder).is_dir():
            issues.append(f"src/components/: falta {folder}/.")
    simple = base / "simple"
    if simple.is_dir():
        for entry in sorted(simple.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".component.tsx"):
                issues.append(f"src/components/simple/{entry.name}: solo archivos *.component.tsx, "
                              "sin subcarpetas ni barrels index.ts.")
    complex_dir = base / "complex"
    if complex_dir.is_dir():
        for entry in sorted(complex_dir.iterdir()):
            if not entry.is_dir():
                issues.append(f"src/components/complex/{entry.name}: cada componente complejo necesita su carpeta.")
                continue
            view = entry / (entry.name + ".component.tsx")
            if not view.is_file():
                issues.append(f"{view.relative_to(root)}: falta vista del componente complejo.")
            for sub in ("hooks", "services"):
                if not (entry / sub).is_dir():
                    issues.append(f"{entry.relative_to(root)}/{sub}/: falta subcarpeta.")
            if (entry / "index.ts").exists():
                issues.append(f"{entry.relative_to(root)}/index.ts: evita barrels en componentes compartidos.")
    for name in changed:
        if name.endswith(".tsx") and name.startswith("src/components/") and (root / name).is_file():
            if re.search(r"\b(?:fetch|axios)\s*\(", text(root, name)):
                issues.append(f"{name}: delega HTTP a services; no lo ejecutes desde componentes compartidos.")
    return issues


def logic_files(root, changed, section, suffix):
    issues = []
    files = []
    for name in sorted(changed):
        if name.endswith("/") or not name.startswith("src/"):
            continue
        parts = Path(name).parts
        if section not in parts:
            continue
        if parts.index(section) == len(parts) - 1:
            continue
        path = root / name
        if not path.is_file():
            continue
        if name.endswith((".ts", ".tsx")):
            if not name.endswith(suffix):
                issues.append(f"{name}: debe terminar en {suffix}.")
            else:
                files.append(name)
    return issues, files


def validate_hooks(root, changed):
    issues, files = logic_files(root, changed, "hooks", ".hook.ts")
    issues += ast_check(root, "hooks", files)
    return issues


def validate_services(root, changed):
    issues, files = logic_files(root, changed, "services", ".service.ts")
    for name in files:
        if re.search(r"\bprocess\.env\b", text(root, name)):
            issues.append(f"{name}: usa import.meta.env en Vite, no process.env.")
    issues += ast_check(root, "services", files)
    return issues


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
            issues.append(f"{path.relative_to(root)}: las páginas deben estar bajo src/modules/, no en routes/.")
    return issues


def validate_modules(root, changed):
    if not changed_in(changed, "modules"):
        return []
    base = root / "src/modules"
    if not base.is_dir():
        return ["src/modules/: falta la carpeta modules."]
    files = [entry.name for entry in base.iterdir() if entry.is_file()]
    if files:
        return ["src/modules/: no pongas archivos sueltos en su raíz: " + ", ".join(sorted(files))]
    return []


def validate_module_routes(root, changed):
    return validate_modules(root, changed) + validate_routes(root, changed)


def validate_api_services(root, changed):
    return validate_api(root, changed) + validate_services(root, changed)

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
    "styles": validate_styles,
    "api": validate_api,
    "components": validate_components,
    "hooks": validate_hooks,
    "services": validate_services,
    "module-routes": validate_module_routes,
    "package": lambda root, changed: validate_config(root, changed) if "package.json" in changed else [],
    "env": lambda root, changed: validate_config(root, changed) if {".env", ".env.example"} & changed else [],
    # Backwards-compatible entry points for old manual commands.
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
