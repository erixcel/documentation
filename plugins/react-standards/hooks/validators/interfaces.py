"""Reglas de interfaces React y sus ámbitos de consumo."""
from pathlib import Path
from analyzers.imports import validate_resource_scopes


def validate_interfaces(root, changed):
    errors = []

    # Regla 1: Los contratos en interface/ o interfaces/ terminan en .interface.ts.
    errors.extend(_validate_interface_names(root, changed))

    # Regla 2: Las interfaces solo se comparten desde ámbitos permitidos.
    errors.extend(_validate_interface_scopes(root, changed))
    return errors


def _validate_interface_names(root, changed):
    issues = []
    for name in sorted(changed):
        file = root / name
        if not file.is_file() or file.suffix not in (".ts", ".tsx"):
            continue
        pieces = Path(name).parts
        if ("interface" in pieces or "interfaces" in pieces) and name.startswith("src/"):
            if not name.endswith(".interface.ts"):
                issues.append(f"{name}: [interface-name] Usa *.interface.ts.")
    return issues


def _validate_interface_scopes(root, changed):
    return validate_resource_scopes(root, changed)
