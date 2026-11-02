"""Erixcel NestJS modular static hook validators; read-only."""
import os
from pathlib import Path
from common.constants import SKIP

def workspace_for(payload):
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_dir():
        return None
    return Path(cwd).resolve()

def source_files(root):
    """Discover files only inside NestJS packages, skipping unrelated workspaces."""
    found = {}
    checked = {}

    def get_project(src):
        if src in checked:
            return checked[src]
        checked[src] = (
            (src / "main.ts").exists()
            or (src / "app.module.ts").exists()
            or (src.parent / "nest-cli.json").exists()
        )
        return checked[src]

    def monitored(path):
        name = path.name
        parts = path.parts
        if name == "tsconfig.json":
            src = path.parent / "src"
            return get_project(src) if src.is_dir() else False
        if name.endswith(".ts") and "scripts" in parts and "src" not in parts:
            # Only root-level scripts for a recognized NestJS package.
            script_index = parts.index("scripts")
            if script_index + 1 == len(parts) - 1:
                src = Path(*parts[:script_index]) / "src"
                return get_project(src) if src.is_dir() else False
        candidates = [a for a in path.parents if a.name == "src"]
        if not candidates:
            return False
        src = candidates[0]
        if not get_project(src):
            return False
        tail = path.relative_to(src).parts
        if len(tail) < 2:
            return name.endswith(".module.ts")
        # The Module Validator covers all NestJS modules, not just src/modules.
        # Track their direct siblings to detect additions and removals as well.
        if name.endswith(".module.ts") or any(path.parent.glob("*.module.ts")):
            return True
        section = tail[0]
        if section == "queries":
            return name.endswith(".query.ts") and len(tail) >= 3
        if section == "core":
            return name.endswith(".core.ts") and len(tail) == 2
        if section == "modules":
            if name.endswith((".controller.ts", ".service.ts", ".module.ts")):
                return True
            if name.endswith(".dto.ts"):
                return "dto" in tail
            if name.endswith(".function.ts") and "functions" in tail[1:-1]:
                return True
            # Track even unknown direct siblings in module folders.
            if any(path.parent.glob("*.module.ts")):
                return True
        if section == "dto":
            return name.endswith(".dto.ts")
        if section == "functions":
            return name.endswith(".function.ts")
        if section == "db" and len(tail) >= 3 and tail[1] == "tables":
            return name.endswith(".table.ts")
        if section == "seeds":
            # Track every file, including JSON in nested directories, to notice
            # prohibited files, edits, new folders and deletions.
            return True
        return False

    for dirname, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        folder = Path(dirname)
        # Directory markers allow detecting creation/removal of even empty
        # directories inside a NestJS src/seeds/ folder.
        for ancestor in folder.parents:
            if ancestor.name == "seeds" and ancestor.parent.name == "src":
                if get_project(ancestor.parent):
                    found[folder.relative_to(root).as_posix() + "/"] = folder
                break
        for name in names:
            path = folder / name
            if not path.is_file() or path.is_symlink() or not monitored(path):
                continue
            found[path.relative_to(root).as_posix()] = path
    return found
