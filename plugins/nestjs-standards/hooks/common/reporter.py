"""Erixcel NestJS modular static hook validators; read-only."""
import json
import os
from common.constants import STATE_ROOT
from datetime import datetime, timezone

def log(event, root, kind, checked, issues):
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "at": datetime.now(timezone.utc).isoformat(), "event": event,
        "workspace": str(root), "validator": kind,
        "checked": checked, "problems": issues,
    }, ensure_ascii=False) + "\n"
    fd = os.open(STATE_ROOT / "query-validator.log", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
