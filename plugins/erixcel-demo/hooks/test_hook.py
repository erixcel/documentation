#!/usr/bin/env python3
"""Hook de prueba: solo registra la ejecucion; no modifica proyectos."""
from datetime import datetime
from pathlib import Path
import json

log_file = Path.home() / ".codex" / "erixcel-demo-hook.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
with log_file.open("a", encoding="utf-8") as f:
    f.write(f"{datetime.now().astimezone().isoformat()} | Hook Erixcel ejecutado\n")

print(json.dumps({}))
