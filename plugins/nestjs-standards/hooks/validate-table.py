#!/usr/bin/env python3
"""Independent Table validation hook (Codex Stop)."""
from validators.table import validate_table
from common.runner import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Table", "table.ts", validate_table,
        "https://docs.erixcel.com/desarrollo/nestjs/src/db/tables",
    ))
