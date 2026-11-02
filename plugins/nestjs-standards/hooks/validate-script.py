#!/usr/bin/env python3
"""Independent Script validation hook (Codex Stop)."""
from validators.script import validate_script
from common.runner import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Script", ".ts", validate_script,
        "https://docs.erixcel.com/desarrollo/nestjs/scripts/index",
    ))
