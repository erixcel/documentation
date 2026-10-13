#!/usr/bin/env python3
"""Independent Function validation hook (Codex Stop)."""
from extra_rules import validate_function
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Function", "function.ts", validate_function,
        "https://docs.erixcel.com/desarrollo/nestjs/src/functions/index",
    ))
