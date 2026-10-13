#!/usr/bin/env python3
"""Erixcel NestJS query guard (Python stdlib only).

UserPromptSubmit snapshots query files. Stop validates only created/changed queries.
No database, network, project-file writes, or shell commands are performed.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_ROOT = Path.home() / ".codex" / "erixcel-query-validator"
SKIP_DIRS = {".git", ".codex", "node_modules", "dist", "build", ".next", "coverage", ".turbo"}
JOIN_RE = re.compile(r"\.\s*(?:leftJoin|rightJoin|innerJoin|fullJoin|crossJoin)\s*\(")
WRITE_RE = re.compile(r"\.\s*(?:insert|update|delete)\s*\(")
TABLE_IMPORT_RE = re.compile(
    r"""(?m)^[ \t]*import\b[\s\S]*?\bfrom\s*['"]([^'"]+)['"]"""
)


def is_table_module(module):
    return module.endswith((".table", ".table.ts", ".table.js"))


def query_files(workspace):
    """Only src/queries directories within the current workspace (monorepo-safe)."""
    found = {}
    for parent, dirs, files in os.walk(workspace, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        folder = Path(parent)
        if folder.name == "queries" and folder.parent.name == "src":
            for p in folder.rglob("*.query.ts"):
                if p.is_file() and not p.is_symlink():
                    try:
                        found[p.relative_to(workspace).as_posix()] = p
                    except ValueError:
                        continue
            dirs[:] = []  # We already traversed this subtree.
    return found


def fingerprints(files):
    hashes = {}
    for name, path in files.items():
        try:
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return hashes


def state_path(payload, workspace):
    key = "\0".join([
        str(payload.get("session_id", "")),
        str(payload.get("turn_id", "")),
        str(workspace),
    ])
    return STATE_ROOT / "snapshots" / (hashlib.sha256(key.encode()).hexdigest() + ".json")


def validate(path):
    """Return actionable diagnostic strings; heuristic, not a TS parser."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"No se pudo leer: {exc}"]
    # Avoid counting imports commented out on their own lines.
    code = re.sub(r"/\*[\s\S]*?\*/|(?m:^[ \t]*//[^\n]*)", "", content)
    imports = [m.group(1) for m in TABLE_IMPORT_RE.finditer(code)]
    tables = sorted(set(module for module in imports if is_table_module(module)))
    errors = []
    is_join = path.name.endswith("-join.query.ts")
    if is_join:
        for match in WRITE_RE.finditer(code):
            line = code.count("\n", 0, match.start()) + 1
            errors.append(f"Línea {line}: archivos -join.query.ts son de solo lectura; prohibido {match.group().strip()}.")
    else:
        if len(tables) != 1:
            errors.append(
                f"Se requiere exactamente 1 tabla importada desde *.table; encontradas {len(tables)}"
                + (f": {', '.join(tables)}." if tables else ".")
            )
        for match in JOIN_RE.finditer(code):
            line = code.count("\n", 0, match.start()) + 1
            errors.append(f"Línea {line}: JOIN prohibido en .query.ts; muévelo a -join.query.ts.")
    return errors


def write_log(event, workspace, changed, problems):
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    with (STATE_ROOT / "query-validator.log").open("a", encoding="utf-8") as log:
        log.write(json.dumps({
            "at": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "cwd": str(workspace),
            "checked": changed,
            "problems": problems,
        }, ensure_ascii=False) + "\n")


def handler(payload):
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_dir():
        return {"systemMessage": "Erixcel Query Validator: cwd no disponible; no se validó."}
    workspace = Path(cwd).resolve()
    event = payload.get("hook_event_name")
    state = state_path(payload, workspace)
    if event == "UserPromptSubmit":
        state.parent.mkdir(parents=True, exist_ok=True)
        snapshot = fingerprints(query_files(workspace))
        state.write_text(json.dumps(snapshot), encoding="utf-8")
        return {}
    if event != "Stop":
        return {}
    if not state.exists():
        return {"systemMessage": "Erixcel Query Validator: no hubo snapshot de inicio para este turno; validación omitida. Inicia otra interacción."}
    before = json.loads(state.read_text(encoding="utf-8"))
    current = query_files(workspace)
    after = fingerprints(current)
    changed = sorted(name for name, hash_value in after.items() if before.get(name) != hash_value)
    issues = []
    for name in changed:
        for problem in validate(current[name]):
            issues.append(f"{name}: {problem}")
    write_log(event, workspace, changed, issues)
    if not issues:
        return {}
    message = (
        "Erixcel Query Validator detectó violaciones en archivos de este turno:\n"
        + "\n".join(f"- {msg}" for msg in issues[:20])
        + "\nConsulta https://docs.erixcel.com/desarrollo/nestjs/src/queries-guia "
        + "y corrige solo esos archivos, sin modificar otros. Después vuelve a comprobarlos."
    )
    # A Stop continuation may run Stop again; never trigger infinite repair loops.
    if payload.get("stop_hook_active"):
        return {"systemMessage": message + "\nSe evitó otro ciclo automático."}
    return {"decision": "block", "reason": message}


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--check":
        failures = []
        for name in sys.argv[2:]:
            path = Path(name)
            if not path.is_file() or not path.name.endswith(".query.ts"):
                failures.append(f"{name}: archivo .query.ts inexistente")
                continue
            failures.extend(f"{name}: {err}" for err in validate(path))
        if failures:
            print("\n".join(failures))
            return 1
        print("Erixcel Query Validator: OK")
        return 0
    try:
        payload = json.load(sys.stdin)
        print(json.dumps(handler(payload), ensure_ascii=False))
    except Exception as exc:
        # Stop expects JSON stdout. Avoid exposing any file contents.
        print(json.dumps({"systemMessage": f"Erixcel Query Validator: error al validar ({type(exc).__name__})."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
