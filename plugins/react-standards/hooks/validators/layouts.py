"""Reglas para secciones internas de layout en páginas React."""
PAGE_RESOURCE_DIRS = {"components", "functions", "hooks", "interface", "interfaces",
                      "pages", "services", "stores", "layout", "data"}


def validate_layout_files(root, changed):
    if not any(name.startswith("src/pages/") for name in changed):
        return []

    errors = []
    for folder in (root / "src/pages").rglob("layout"):
        if not folder.is_dir() or folder.is_symlink():
            continue

        # Regla 1: Un layout no puede contener ninguna subcarpeta pages/.
        errors.extend(_validate_layout_no_pages(root, folder))

        for section in folder.iterdir():
            if not section.is_dir() or section.name == "pages":
                continue
            view = section / (section.name + ".layout.tsx")

            # Regla 2: Cada sección de layout necesita su vista propia.
            errors.extend(_validate_layout_section_view(root, section, view))

            # Regla 3: No pueden coexistir otras vistas TSX al nivel de la sección.
            errors.extend(_validate_layout_section_names(root, section, view))
    return errors


def _validate_layout_no_pages(root, folder):
    errors = []
    for item in folder.rglob("*"):
        if item.is_dir() and item.name == "pages":
            errors.append(f"{item.relative_to(root)}: [layout-pages] Un layout no puede contener pages/.")
    return errors


def _validate_layout_section_view(root, section, view):
    if not view.is_file():
        return [f"{section.relative_to(root)}: [layout-required] Falta {view.name}."]
    return []


def _validate_layout_section_names(root, section, view):
    errors = []
    for item in section.iterdir():
        if item.is_file() and item.suffix == ".tsx" and item.name != view.name:
            errors.append(f"{item.relative_to(root)}: [layout-name] La sección utiliza {view.name}.")
    return errors
