"""Erixcel NestJS modular static hook validators; read-only."""
import hashlib
import json
from pathlib import Path
from common.constants import STATE_ROOT
from common.discovery import source_files

def hashes(files):
    result = {}
    for name, path in files.items():
        try:
            if path.is_dir():
                result[name] = "<directory>"
            else:
                result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return result

def snapshot_path(payload, root):
    key = "\x00".join([
        str(payload.get("session_id", "")),
        str(payload.get("turn_id", "")),
        str(root),
    ])
    return STATE_ROOT / "snapshots" / (hashlib.sha256(key.encode()).hexdigest() + ".json")

def read_snapshot(payload, root):
    path = snapshot_path(payload, root)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid snapshot")
    return data

def store_snapshot(payload, root):
    target = snapshot_path(payload, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(hashes(source_files(root)))
    temporary = target.with_name(target.name + "." + str(os.getpid()))
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
