"""Shared turn snapshots, discovery, reporting for Erixcel validators.

Never modifies repository files, never connects to PostgreSQL.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_ROOT = Path.home() / ".codex" / "erixcel-query-validator"
SKIP = {".git", ".codex", "node_modules", "dist", "build", ".next", "coverage", ".turbo"}


def workspace_for(payload):
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_dir():
        return None
    return Path(cwd).resolve()


def source_files(root):
    """Discover files only inside NestJS packages, skipping unrelated workspaces."""
    found = {}
    checked = {}

    def get_project(src):
        if src in checked:
            return checked[src]
        checked[src] = (
            (src / "main.ts").exists()
            or (src / "app.module.ts").exists()
            or (src.parent / "nest-cli.json").exists()
        )
        return checked[src]

    def monitored(path):
        name = path.name
        parts = path.parts
        if name == "tsconfig.json":
            src = path.parent / "src"
            return get_project(src) if src.is_dir() else False
        if name.endswith(".ts") and "scripts" in parts and "src" not in parts:
            # Only root-level scripts for a recognized NestJS package.
            script_index = parts.index("scripts")
            if script_index + 1 == len(parts) - 1:
                src = Path(*parts[:script_index]) / "src"
                return get_project(src) if src.is_dir() else False
        candidates = [a for a in path.parents if a.name == "src"]
        if not candidates:
            return False
        src = candidates[0]
        if not get_project(src):
            return False
        tail = path.relative_to(src).parts
        if len(tail) < 2:
            return name.endswith(".module.ts")
        # The Module Validator covers all NestJS modules, not just src/modules.
        # Track their direct siblings to detect additions and removals as well.
        if name.endswith(".module.ts") or any(path.parent.glob("*.module.ts")):
            return True
        section = tail[0]
        if section == "queries":
            return name.endswith(".query.ts") and len(tail) >= 3
        if section == "core":
            return name.endswith(".core.ts") and len(tail) == 2
        if section == "modules":
            if name.endswith((".controller.ts", ".service.ts", ".module.ts")):
                return True
            if name.endswith(".dto.ts"):
                return "dto" in tail
            if name.endswith(".function.ts") and "functions" in tail[1:-1]:
                return True
            # Track even unknown direct siblings in module folders.
            if any(path.parent.glob("*.module.ts")):
                return True
        if section == "dto":
            return name.endswith(".dto.ts")
        if section == "functions":
            return name.endswith(".function.ts")
        if section == "db" and len(tail) >= 3 and tail[1] == "tables":
            return name.endswith(".table.ts")
        if section == "seeds":
            # Track every file, including JSON in nested directories, to notice
            # prohibited files, edits, new folders and deletions.
            return True
        return False

    for dirname, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        folder = Path(dirname)
        # Directory markers allow detecting creation/removal of even empty
        # directories inside a NestJS src/seeds/ folder.
        for ancestor in folder.parents:
            if ancestor.name == "seeds" and ancestor.parent.name == "src":
                if get_project(ancestor.parent):
                    found[folder.relative_to(root).as_posix() + "/"] = folder
                break
        for name in names:
            path = folder / name
            if not path.is_file() or path.is_symlink() or not monitored(path):
                continue
            found[path.relative_to(root).as_posix()] = path
    return found


def hashes(files):
    result = {}
    for name, path in files.items():
        try:
            if path.is_dir():
                result[name] = "<directory>"
            else:
                result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return result


def snapshot_path(payload, root):
    key = "\x00".join([
        str(payload.get("session_id", "")),
        str(payload.get("turn_id", "")),
        str(root),
    ])
    return STATE_ROOT / "snapshots" / (hashlib.sha256(key.encode()).hexdigest() + ".json")


def read_snapshot(payload, root):
    path = snapshot_path(payload, root)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid snapshot")
    return data


def store_snapshot(payload, root):
    target = snapshot_path(payload, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(hashes(source_files(root)))
    temporary = target.with_name(target.name + "." + str(os.getpid()))
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()


def log(event, root, kind, checked, issues):
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "at": datetime.now(timezone.utc).isoformat(), "event": event,
        "workspace": str(root), "validator": kind,
        "checked": checked, "problems": issues,
    }, ensure_ascii=False) + "\n"
    fd = os.open(STATE_ROOT / "query-validator.log", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def validate_seed_directory(folder):
    """Only *.seed.ts files directly in src/seeds; no other files or folders."""
    if not folder.is_dir():
        return []
    invalid_files = sorted(
        entry.name for entry in folder.iterdir()
        if not entry.is_dir() and not (
            entry.is_file() and not entry.is_symlink()
            and entry.name.endswith(".seed.ts")
        )
    )
    invalid_dirs = sorted(entry.name + "/" for entry in folder.iterdir() if entry.is_dir())
    problems = []
    if invalid_files:
        problems.append(
            "Archivos no permitidos directamente en " + str(folder)
            + ": " + ", ".join(invalid_files)
            + ". Solo archivos *.seed.ts. Guarda los datos iniciales dentro "
              "de la función seed correspondiente."
        )
    if invalid_dirs:
        problems.append(
            "Subcarpetas prohibidas dentro de " + str(folder)
            + ": " + ", ".join(invalid_dirs)
            + ". src/seeds/ debe ser plano: solo *.seed.ts. Migra los JSON "
              "de data/ a arrays/objetos locales dentro del seed que los usa, "
              "verifica referencias y elimina la carpeta solo cuando sea seguro."
        )
    return problems


def seed_root_relative(name):
    """Return the relative src/seeds directory for a tracked path, or None."""
    marker = "/src/seeds/"
    full = "/" + name
    if marker not in full:
        return None
    prefix = full.split(marker, 1)[0].lstrip("/")
    return (prefix + "/src/seeds").lstrip("/")


def check_turn(payload, kind, suffix, validator, documentation):
    if payload.get("hook_event_name") != "Stop":
        return {}
    root = workspace_for(payload)
    if root is None:
        return {"systemMessage": f"Erixcel {kind}: carpeta del proyecto no disponible."}
    before = read_snapshot(payload, root)
    if before is None:
        return {"systemMessage": f"Erixcel {kind}: no se encontró el snapshot de UserPromptSubmit; comprobación omitida."}
    current = source_files(root)
    after = hashes(current)
    modified = sorted(
        name for name, sha in after.items()
        if name.endswith(suffix) and (kind != "Script" or "/scripts/" in "/" + name) and before.get(name) != sha
    )
    seed_directories = set()
    if kind == "Seed":
        changed = {
            name for name in (set(before) | set(after))
            if before.get(name) != after.get(name)
        }
        seed_directories = {
            seed_root_relative(name) for name in changed
            if seed_root_relative(name) is not None
        }
        # A JSON edit, a newly created empty directory, or deleting a seed
        # must recheck the seed directory even without changing *.seed.ts.
        if seed_directories:
            modified = sorted({
                name for name in current
                if name.endswith(".seed.ts")
                and str(Path(name).parent) in seed_directories
            })
    if kind == "Controller":
        # A DTO created, edited, or deleted also rechecks its sibling Controller(s).
        dto_changes = {
            name for name in set(before) | set(after)
            if name.endswith(".dto.ts")
            and "/modules/" in "/" + name
            and "/dto/" in name
            and before.get(name) != after.get(name)
        }
        affected = {str(Path(name).parent.parent) for name in dto_changes}
        modified = sorted(set(modified) | {
            name for name in current
            if name.endswith(".controller.ts")
            and str(Path(name).parent) in affected
        })
    if kind == "Module":
        # Recheck parent module(s) too: nesting violations can be introduced by
        # creating a loose child module without editing the parent's .module.ts.
        touched_modules = set(modified)
        changed_paths = {
            name for name in set(before) | set(after)
            if "/src/" in "/" + name and before.get(name) != after.get(name)
        }
        for name in changed_paths:
            directory = Path(name).parent
            for ancestor in (directory, *directory.parents):
                if ancestor.name == "src":
                    break
                candidate = (ancestor / (ancestor.name + ".module.ts")).as_posix()
                if candidate in current:
                    touched_modules.add(candidate)
        modified = sorted(
            name for name in touched_modules
            if name in current
            and not (name == "src/app.module.ts" or name.endswith("/src/app.module.ts"))
        )
    issues = []
    if kind == "Seed":
        for directory in sorted(seed_directories):
            issues.extend(
                f"{directory}: {error}"
                for error in validate_seed_directory(root / directory)
            )
    for name in modified:
        issues.extend(f"{name}: {error}" for error in validator(current[name]))
    log("Stop", root, kind, modified + sorted(seed_directories), issues)
    if not issues:
        return {}
    message = (
        f"Erixcel {kind}: errores en archivos modificados durante este turno:\n"
        + "\n".join("- " + issue for issue in issues[:20])
        + "\nConvenciones: " + documentation
        + "\nCorrige los archivos señalados y vuelve a comprobarlos."
    )
    if payload.get("stop_hook_active"):
        return {"systemMessage": message + "\nSin nuevo bloqueo para evitar bucles."}
    return {"decision": "block", "reason": message}


def run(kind, suffix, validator, docs):
    if len(sys.argv) >= 2 and sys.argv[1] == "--check":
        issues = []
        for name in sys.argv[2:]:
            path = Path(name)
            if kind == "Seed" and path.is_dir() and path.name == "seeds":
                issues.extend(f"{name}: {x}" for x in validate_seed_directory(path))
                for seed in sorted(path.glob("*.seed.ts")):
                    issues.extend(f"{seed}: {x}" for x in validator(seed))
            elif path.is_file() and path.name.endswith(suffix):
                if kind == "Seed":
                    issues.extend(
                        f"{path.parent}: {x}" for x in validate_seed_directory(path.parent)
                    )
                issues.extend(f"{name}: {item}" for item in validator(path))
            else:
                issues.append(f"{name}: ruta inválida para {kind}.")
        if issues:
            print("\n".join(issues))
            return 1
        print(f"Erixcel {kind}: OK")
        return 0
    try:
        payload = json.load(sys.stdin)
        print(json.dumps(check_turn(payload, kind, suffix, validator, docs), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"systemMessage": f"Erixcel {kind}: error {type(exc).__name__}; validación incompleta."}, ensure_ascii=False))
    return 0
