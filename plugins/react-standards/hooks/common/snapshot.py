"""Erixcel React hook validation; read-only."""
import hashlib
import json
from pathlib import Path
from common.constants import STATE
from common.discovery import discover

def snapshot_id(payload, root):
    turn = str(payload.get("session_id") or payload.get("conversation_id") or "local")
    return hashlib.sha256((str(root) + "::" + turn).encode()).hexdigest()[:32]

def fingerprint(path):
    try:
        if path.is_dir():
            return "<directory>"
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2", ".mp4", ".gif"}:
            s = path.stat()
            return str(s.st_size) + ":" + str(s.st_mtime_ns)
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "<unreadable>"

def snapshot(root):
    return {name: fingerprint(path) for name, path in discover(root).items()}

def store(payload, root):
    STATE.mkdir(parents=True, exist_ok=True)
    state = STATE / (snapshot_id(payload, root) + ".json")
    data = {"root": str(root), "files": snapshot(root)}
    # No file contents, especially no .env values, are stored.
    temp = state.with_suffix(".tmp")
    temp.write_text(json.dumps(data), encoding="utf-8")
    temp.replace(state)

def load(payload, root):
    state = STATE / (snapshot_id(payload, root) + ".json")
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
        return data.get("files") if data.get("root") == str(root) else None
    except (OSError, ValueError, TypeError):
        return None
