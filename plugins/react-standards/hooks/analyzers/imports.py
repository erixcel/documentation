"""Erixcel React hook validation; read-only."""
import re
from pathlib import Path
from common.constants import SKIP
from common.discovery import text

RESOURCE_SUFFIXES = {
    "functions": ".function.ts", "hooks": ".hook.ts",
    "services": ".service.ts", "interfaces": ".interface.ts",
    "stores": ".store.ts",
}
IMPORT_RE = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(|\bimport\s*)['"]([^'"]+)['"]""")

def resource_scope(name):
    """Return page/section directory (or src) owning a resource."""
    parts = Path(name).parts
    if len(parts) < 3 or parts[0] != "src":
        return None
    if parts[1] != "pages":
        return Path("src")
    if len(parts) < 3:
        return None
    # Page boundaries are explicit: src/pages/admin/pages/users.
    scope = ["src", "pages", parts[2]]
    pos = 3
    while pos + 1 < len(parts) and parts[pos] == "pages":
        scope.extend(parts[pos:pos+2])
        pos += 2
    return Path(*scope)

def resource_kind(name):
    parts = Path(name).parts
    if not parts or not name.startswith("src/"):
        return None
    for folder, suffix in RESOURCE_SUFFIXES.items():
        if folder in parts and parts[-2] == folder:
            return folder, suffix
    if "components" in parts and parts[-1].endswith((".ts", ".tsx")):
        idx = parts.index("components")
        if len(parts) > idx + 2 and parts[idx+1] in ("simple", "complex"):
            if parts[idx+1] == "simple" or (parts[-2] == parts[idx+2] and parts[-1].endswith(".tsx")):
                return "components", ".component.tsx"
        return None
    return None

def resolve_relative_import(root, source, target):
    if not target.startswith("."):
        return None  # aliases and package imports cannot be verified here
    base = root / source
    stem = base.parent / target
    for candidate in [stem, *[Path(str(stem) + ext) for ext in (".ts", ".tsx")],
                      stem / "index.ts", stem / "index.tsx"]:
        try:
            resolved = candidate.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if (root / resolved).is_file():
            return resolved.as_posix()
    return None

def validate_resource_scopes(root, changed):
    """Check resource suffixes and provable import boundaries; avoid guessing dynamic consumers."""
    if not any(n.startswith("src/") for n in changed):
        return []
    issues = []
    resources = {}
    for path in (root / "src").rglob("*"):
        if not path.is_file() or path.is_symlink() or any(x in SKIP for x in path.parts):
            continue
        name = path.relative_to(root).as_posix()
        kind = resource_kind(name)
        if kind:
            resources[name] = (kind[0], resource_scope(name))
            folder, suffix = kind
            if name in changed and not name.endswith(suffix) and path.suffix in (".ts", ".tsx"):
                issues.append(f"{name}: [resource-suffix] En {folder}/ usa *{suffix}.")
            if folder == "components" and name in changed and name.endswith(".component.tsx"):
                parts = Path(name).parts
                at = parts.index("components")
                if len(parts) <= at+2 or parts[at+1] not in ("simple", "complex"):
                    issues.append(f"{name}: [component-location] Usa components/simple/ o components/complex/ también dentro de páginas.")
    for path in (root / "src").rglob("*"):
        if not path.is_file() or path.suffix not in (".ts", ".tsx") or path.is_symlink() or any(x in SKIP for x in path.parts):
            continue
        importer = path.relative_to(root).as_posix()
        if importer not in changed and not resources.keys() & changed:
            continue
        for spec in IMPORT_RE.findall(text(root, importer)):
            resolved = resolve_relative_import(root, importer, spec)
            if not resolved or resolved not in resources:
                continue
            kind, owner = resources[resolved]
            if owner is None:
                continue
            consumer = resource_scope(importer)
            if consumer is None:
                continue
            if consumer != owner and owner not in consumer.parents:
                issues.append(f"{importer}: [resource-scope] Importa {resolved} desde fuera de su ámbito. Mueve el recurso al ancestro común más cercano y ajusta imports.")
            if Path(resolved).name.startswith("index.") and kind in ("components", "stores", "hooks", "services", "functions", "interfaces"):
                issues.append(f"{importer}: [resource-barrel] Importa recursos privados directamente, sin index.ts.")
    return sorted(set(issues))
