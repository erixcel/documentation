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
            return name.endswith(".module.ts") and name == "app.module.ts"
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
        if section == "dto":
            return name.endswith(".dto.ts")
        if section == "functions":
            return name.endswith(".function.ts")
        if section == "db" and len(tail) >= 3 and tail[1] == "tables":
            return name.endswith(".table.ts")
        if section == "seeds":
            return name.endswith(".seed.ts")
        return False

    for dirname, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        folder = Path(dirname)
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
    issues = []
    for name in modified:
        issues.extend(f"{name}: {error}" for error in validator(current[name]))
    log("Stop", root, kind, modified, issues)
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
            if not path.is_file() or not path.name.endswith(suffix):
                issues.append(f"{name}: ruta inválida para {kind}.")
            else:
                issues.extend(f"{name}: {item}" for item in validator(path))
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
