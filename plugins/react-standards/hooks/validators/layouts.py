"""Erixcel React hook validation; read-only."""
from pathlib import Path

PAGE_RESOURCE_DIRS = {"components", "functions", "hooks", "interface", "interfaces",
                      "pages", "services", "stores", "layout", "data"}

def validate_layout_files(root, changed):
    if not any(n.startswith("src/pages/") for n in changed):
        return []
    issues = []
    for folder in (root / "src/pages").rglob("layout"):
        if not folder.is_dir() or folder.is_symlink():
            continue
        rel = folder.relative_to(root).as_posix()
        for item in folder.rglob("*"):
            if item.is_dir() and item.name == "pages":
                issues.append(f"{item.relative_to(root)}: [layout-pages] Un layout no puede contener pages/.")
        for section in folder.iterdir():
            if not section.is_dir() or section.name == "pages":
                continue
            view = section / (section.name + ".layout.tsx")
            if not view.is_file():
                issues.append(f"{section.relative_to(root)}: [layout-required] Falta {view.name}.")
            # Nested components retain their .component.tsx suffix.
            for item in section.iterdir():
                if item.is_file() and item.suffix == ".tsx" and item.name != view.name:
                    issues.append(f"{item.relative_to(root)}: [layout-name] La sección utiliza {view.name}.")
    return issues
