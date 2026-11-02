"""Erixcel React hook validation; read-only."""
from pathlib import Path
from common.constants import SKIP
from common.discovery import changed_in
from validators.routes import validate_routes

def validate_pages(root, changed):
    if not any(n.startswith("src/pages/") for n in changed):
        return []
    base = root / "src/pages"
    if not base.is_dir():
        return ["src/pages/: falta la carpeta pages."]
    files = [entry.name for entry in base.iterdir() if entry.is_file()]
    if files:
        return ["src/pages/: no pongas archivos sueltos en su raíz: " + ", ".join(sorted(files))]
    return []

def validate_page_routes(root, changed):
    return validate_pages(root, changed) + validate_routes(root, changed)

def page_roots(root):
    base = root / "src/pages"
    if not base.is_dir():
        return []
    roots = []
    for folder in base.rglob("*"):
        if not folder.is_dir() or folder.is_symlink() or any(p in SKIP for p in folder.parts):
            continue
        relative = folder.relative_to(base).parts
        if relative and (len(relative) == 1 or relative[-2] == "pages"):
            roots.append(folder)
    return roots

def validate_page_files(root, changed):
    if not changed_in(changed, "pages"):
        return []
    issues = []
    for folder in page_roots(root):
        rel = folder.relative_to(root).as_posix()
        expected = folder / (folder.name + ".page.tsx")
        if not expected.is_file():
            issues.append(f"{rel}: [page-required] La página necesita {expected.name}.")
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix == ".tsx" and entry.name != expected.name:
                issues.append(f"{rel}/{entry.name}: [page-name] Usa {expected.name} para la vista de esta página.")
        # Subpages are only children of a page's pages/, never under layout/.
        child = folder / "pages"
        if child.is_dir():
            for entry in child.iterdir():
                if entry.is_file() and entry.suffix in (".ts", ".tsx"):
                    issues.append(f"{rel}/pages/{entry.name}: [page-folder] Cada subpágina necesita su carpeta.")
    return issues
