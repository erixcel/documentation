"""Erixcel NestJS modular static hook validators; read-only."""
import json
import sys
from pathlib import Path
from common.discovery import workspace_for, source_files
from common.snapshot import hashes, read_snapshot
from common.reporter import log
from validators.seed import validate_seed_directory, seed_root_relative

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
