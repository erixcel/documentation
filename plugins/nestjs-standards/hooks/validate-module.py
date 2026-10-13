#!/usr/bin/env python3
"""Independent Module validation hook (Codex Stop)."""
from extra_rules import validate_module
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Module", "module.ts", validate_module,
        "https://docs.erixcel.com/desarrollo/nestjs/src/modules-guia",
    ))
