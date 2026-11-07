"""Reglas de páginas y subpáginas React con vistas *.page.tsx."""
from common.constants import SKIP
from common.discovery import changed_in
from validators.routes import validate_routes


def validate_page_files(root, changed):
    if not changed_in(changed, "pages"):
        return []
    issues = []
    for folder in page_roots(root):
        rel = folder.relative_to(root).as_posix()
        expected = folder / (folder.name + ".page.tsx")

        # Regla 1: Cada página requiere una vista llamada <carpeta>.page.tsx.
        issues.extend(_validate_page_required_view(rel, expected))

        # Regla 2: No deben existir otras vistas .tsx sueltas en una página.
        issues.extend(_validate_page_view_name(rel, folder, expected))

        # Regla 3: Cada subpágina requiere su propia carpeta en pages/.
        issues.extend(_validate_page_subpage_directories(rel, folder))
    return issues


def _validate_page_required_view(rel, expected):
    if not expected.is_file():
        return [f"{rel}: [page-required] La página necesita {expected.name}."]
    return []


def _validate_page_view_name(rel, folder, expected):
    issues = []
    for entry in folder.iterdir():
        if entry.is_file() and entry.suffix == ".tsx" and entry.name != expected.name:
            issues.append(f"{rel}/{entry.name}: [page-name] Usa {expected.name} para la vista de esta página.")
    return issues


def _validate_page_subpage_directories(rel, folder):
    issues = []
    child = folder / "pages"
    if child.is_dir():
        for entry in child.iterdir():
            if entry.is_file() and entry.suffix in (".ts", ".tsx"):
                issues.append(f"{rel}/pages/{entry.name}: [page-folder] Cada subpágina necesita su carpeta.")
    return issues


def page_roots(root):
    """Enumerar carpetas que son páginas principales o subpáginas."""
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


def validate_pages(root, changed):
    """Regla adicional de páginas heredada para comprobación manual."""
    if not any(name.startswith("src/pages/") for name in changed):
        return []
    base = root / "src/pages"

    # Regla 4: La carpeta src/pages/ debe existir.
    if not base.is_dir():
        return _validate_pages_root(base)

    # Regla 5: La raíz de src/pages/ no admite archivos sueltos.
    return _validate_pages_loose_files(base)


def _validate_pages_root(base):
    if not base.is_dir():
        return ["src/pages/: falta la carpeta pages."]
    return []


def _validate_pages_loose_files(base):
    files = [entry.name for entry in base.iterdir() if entry.is_file()]
    if files:
        return ["src/pages/: no pongas archivos sueltos en su raíz: " + ", ".join(sorted(files))]
    return []


def validate_page_routes(root, changed):
    """Compatibilidad con el modo manual de validación páginas + rutas."""
    return validate_pages(root, changed) + validate_routes(root, changed)
