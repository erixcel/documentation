"""Reglas de componentes React simples y complejos."""
import re
from common.discovery import changed_in, text


def validate_components(root, changed):
    if not changed_in(changed, "components"):
        return []
    base = root / "src/components"
    issues = []

    # Regla 1: Debe existir la carpeta de componentes.
    if not base.is_dir():
        return _validate_components_directory(base)

    # Regla 2: La raíz de components/ contiene solo simple/ y complex/.
    issues.extend(_validate_components_root_entries(base))

    # Regla 3: Ambas subcarpetas simple/ y complex/ deben existir.
    issues.extend(_validate_components_required_folders(base))

    # Regla 4: simple/ solo admite archivos *.component.tsx.
    issues.extend(_validate_components_simple_files(base))

    # Regla 5: complex/ contiene carpetas con vista y recursos internos.
    issues.extend(_validate_components_complex_files(root, base))

    # Regla 6: Los componentes compartidos no ejecutan peticiones HTTP.
    issues.extend(_validate_components_no_http(root, changed))
    return issues


def _validate_components_directory(base):
    if not base.is_dir():
        return ["src/components/: falta carpeta components."]
    return []


def _validate_components_root_entries(base):
    issues = []
    for entry in sorted(base.iterdir()):
        if entry.name not in ("simple", "complex") or not entry.is_dir():
            issues.append(f"src/components/{entry.name}: en la raíz solo existen simple/ y complex/.")
    return issues


def _validate_components_required_folders(base):
    issues = []
    for folder in ("simple", "complex"):
        if not (base / folder).is_dir():
            issues.append(f"src/components/: falta {folder}/.")
    return issues


def _validate_components_simple_files(base):
    issues = []
    simple = base / "simple"
    if simple.is_dir():
        for entry in sorted(simple.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".component.tsx"):
                issues.append(
                    f"src/components/simple/{entry.name}: solo archivos *.component.tsx, "
                    "sin subcarpetas ni barrels index.ts."
                )
    return issues


def _validate_components_complex_files(root, base):
    issues = []
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
    return issues


def _validate_components_no_http(root, changed):
    issues = []
    for name in changed:
        if name.endswith(".tsx") and name.startswith("src/components/") and (root / name).is_file():
            if re.search(r"\b(?:fetch|axios)\s*\(", text(root, name)):
                issues.append(f"{name}: delega HTTP a services; no lo ejecutes desde componentes compartidos.")
    return issues
