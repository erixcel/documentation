"""Erixcel React hook validation; read-only."""
import re
from pathlib import Path
from common.discovery import changed_in, text

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
