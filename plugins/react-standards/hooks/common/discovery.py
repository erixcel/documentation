"""Erixcel React hook validation; read-only."""
import json
import os
import re
from pathlib import Path
from common.constants import SKIP

def project_for(payload):
    cwd = payload.get("cwd")
    if not isinstance(cwd, str):
        return None
    here = Path(cwd).resolve()
    if not here.is_dir():
        return None
    candidates = [here, here / "frontend"]
    candidates += [parent for parent in here.parents if parent != Path(parent.anchor)]
    for candidate in candidates:
        if looks_like_react(candidate):
            return candidate
    for base, dirs, files in os.walk(here):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        path = Path(base)
        if path != here and len(path.relative_to(here).parts) > 3:
            dirs[:] = []
            continue
        if looks_like_react(path):
            return path
    return None

def looks_like_react(root):
    package = root / "package.json"
    if not package.is_file() or not (root / "src").is_dir():
        return False
    try:
        cfg = json.loads(package.read_text(encoding="utf-8"))
        libs = {**cfg.get("dependencies", {}), **cfg.get("devDependencies", {})}
        return "react" in libs and "vite" in libs
    except (OSError, ValueError, TypeError):
        return False

def discover(root):
    result = {}
    for name in ("package.json", ".env", ".env.example"):
        file = root / name
        if file.is_file():
            result[name] = file
    src = root / "src"
    if src.is_dir():
        result["src/"] = src
        for parent, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in SKIP)
            base = Path(parent)
            if base != src:
                result[base.relative_to(root).as_posix() + "/"] = base
            for file in files:
                path = base / file
                if not path.is_symlink() and path.is_file():
                    result[path.relative_to(root).as_posix()] = path
    return result

def text(root, name):
    try:
        return (root / name).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""

def changed_in(changed, segment):
    return any(name.startswith("src/" + segment + "/")
               or ("/" + segment + "/") in name
               for name in changed)

def logic_files(root, changed, section, suffix):
    issues = []
    files = []
    for name in sorted(changed):
        if name.endswith("/") or not name.startswith("src/"):
            continue
        parts = Path(name).parts
        if section not in parts:
            continue
        if parts.index(section) == len(parts) - 1:
            continue
        path = root / name
        if not path.is_file():
            continue
        if name.endswith((".ts", ".tsx")):
            if not name.endswith(suffix):
                issues.append(f"{name}: debe terminar en {suffix}.")
            else:
                files.append(name)
    return issues, files
