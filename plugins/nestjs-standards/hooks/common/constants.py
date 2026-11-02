"""Erixcel NestJS modular static hook validators; read-only."""
from pathlib import Path
STATE_ROOT = Path.home() / ".codex" / "erixcel-query-validator"
SKIP = {".git", ".codex", "node_modules", "dist", "build", ".next", "coverage", ".turbo"}
