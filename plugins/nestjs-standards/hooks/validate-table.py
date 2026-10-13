#!/usr/bin/env python3
"""Independent Table validation hook (Codex Stop)."""
from extra_rules import validate_table
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Table", "table.ts", validate_table,
        "https://docs.erixcel.com/desarrollo/nestjs/src/db/tables",
    ))
