#!/usr/bin/env python3
"""Independent Script validation hook (Codex Stop)."""
from extra_rules import validate_script
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Script", ".ts", validate_script,
        "https://docs.erixcel.com/desarrollo/nestjs/scripts/index",
    ))
