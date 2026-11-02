"""Erixcel React hook validation; read-only."""
import json
import sys
from pathlib import Path
from common.constants import DESCRIPTIONS
from common.discovery import project_for, looks_like_react
from common.snapshot import snapshot, load
from common.reporter import format_reason
from validators.registry import CHECKS

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
    reason = format_reason(kind, errors, doc)
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
