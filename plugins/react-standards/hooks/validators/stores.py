"""Reglas independientes para stores React y sus límites de alcance."""
from pathlib import Path
from common.constants import SKIP
from analyzers.ast import ast_check


def validate_stores(root, changed):
    """Revisar stores modificados, incluidas carpetas movidas o eliminadas."""
    # Regla 1: Identificar archivos y carpetas de stores modificados.
    paths, dirs = _validate_stores_collect_changes(changed)
    if not paths and not dirs:
        return []

    # Regla 2: Incluir los hermanos de carpetas stores afectadas.
    paths = _validate_stores_expand_directories(root, paths, dirs)

    # Regla 3: Comprobar extensiones y ubicación de cada store.
    errors, targets = _validate_stores_names_and_locations(root, paths)

    # Regla 4: Revisar el AST: sin JSX, ReactDOM ni React Hooks.
    errors.extend(_validate_stores_ast(root, targets))

    return errors


def _validate_stores_collect_changes(changed):
    paths = set()
    dirs = set()
    for name in changed:
        if not name.startswith("src/"):
            continue
        pieces = Path(name.rstrip("/")).parts
        if "stores" in pieces or name.endswith((".store.ts", ".store.tsx", ".store.js", ".store.jsx")):
            if name.endswith("/"):
                dirs.add(name.rstrip("/"))
            else:
                paths.add(name)
                dirs.add(str(Path(name).parent).replace("\\", "/"))
    return paths, dirs


def _validate_stores_expand_directories(root, paths, dirs):
    for rel in sorted(dirs):
        folder = root / rel
        if not folder.is_dir() or folder.is_symlink():
            continue
        for entry in folder.iterdir():
            if entry.is_file() and not entry.is_symlink():
                paths.add(entry.relative_to(root).as_posix())
            elif entry.is_dir() and not entry.is_symlink():
                if "stores" in Path(rel).parts:
                    for child in entry.rglob("*"):
                        if child.is_file() and not child.is_symlink() and not any(x in SKIP for x in child.parts):
                            paths.add(child.relative_to(root).as_posix())
    return paths


def _validate_stores_names_and_locations(root, paths):
    errors = []
    targets = []
    for name in sorted(paths):
        file = root / name
        if not file.is_file() or file.is_symlink():
            continue  # Los stores movidos o eliminados no son errores por sí mismos.
        segments = Path(name).parts
        is_store = name.endswith(".store.ts")
        if "stores" not in segments and not is_store and not any(
            name.endswith(suffix) for suffix in (".store.tsx", ".store.js", ".store.jsx")
        ):
            continue
        if not is_store:
            errors.append(f"{name}:1: [store-name] Los archivos de stores deben terminar en .store.ts.")
        if not is_store_path(name):
            errors.append(
                f"{name}:1: [store-location] Ubica stores en src/stores/*.store.ts "
                "o src/pages/<sección>[/subsección]/stores/*.store.ts; "
                "elige según quién comparte el estado."
            )
        if name.endswith((".ts", ".tsx")):
            targets.append(name)
    return errors, targets


def _validate_stores_ast(root, targets):
    return ast_check(root, "stores", targets)


def is_store_path(name):
    """Solo stores globales src/stores/ o privados de páginas y secciones."""
    parts = Path(name).parts
    if len(parts) == 3 and parts[:2] == ("src", "stores"):
        return True
    return (len(parts) >= 5 and parts[:2] == ("src", "pages")
            and parts[-2] == "stores"
            and "stores" not in parts[2:-2]
            and all(part not in (".", "..") for part in parts[2:-2]))
