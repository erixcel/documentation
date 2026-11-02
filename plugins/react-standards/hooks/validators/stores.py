"""Erixcel React hook validation; read-only."""
from pathlib import Path
from common.constants import SKIP
from analyzers.ast import ast_check

def is_store_path(name):
    """Only shared src/stores or private src/pages/<section>[/...]/stores."""
    parts = Path(name).parts
    if len(parts) == 3 and parts[:2] == ("src", "stores"):
        return True
    return (len(parts) >= 5 and parts[:2] == ("src", "pages")
            and parts[-2] == "stores"
            and "stores" not in parts[2:-2]
            and all(part not in (".", "..") for part in parts[2:-2]))

def validate_stores(root, changed):
    """Validate only touched store locations, including directory moves/deletes."""
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

    if not paths and not dirs:
        return []

    # A touched directory can contain unchanged siblings with invalid names.
    for rel in sorted(dirs):
        folder = root / rel
        if not folder.is_dir() or folder.is_symlink():
            continue
        for entry in folder.iterdir():
            if entry.is_file() and not entry.is_symlink():
                paths.add(entry.relative_to(root).as_posix())
            elif entry.is_dir() and not entry.is_symlink():
                # Traverse only folders in/under a touched stores area.
                if "stores" in Path(rel).parts:
                    for child in entry.rglob("*"):
                        if child.is_file() and not child.is_symlink() and not any(x in SKIP for x in child.parts):
                            paths.add(child.relative_to(root).as_posix())

    errors = []
    targets = []
    for name in sorted(paths):
        file = root / name
        if not file.is_file() or file.is_symlink():
            continue  # Deleted/moved stores are not automatically errors.
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
    errors.extend(ast_check(root, "stores", targets))
    return errors
