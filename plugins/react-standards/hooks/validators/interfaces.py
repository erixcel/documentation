"""Erixcel React hook validation; read-only."""
from pathlib import Path
from analyzers.imports import validate_resource_scopes

def validate_interfaces(root, changed):
    issues = []
    for name in sorted(changed):
        file = root / name
        if not file.is_file() or file.suffix not in (".ts", ".tsx"):
            continue
        pieces = Path(name).parts
        if ("interface" in pieces or "interfaces" in pieces) and name.startswith("src/"):
            if not name.endswith(".interface.ts"):
                issues.append(f"{name}: [interface-name] Usa *.interface.ts.")
    return issues + validate_resource_scopes(root, changed)
