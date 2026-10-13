#!/usr/bin/env python3
"""Independent Controller validation hook (Codex Stop)."""
from extra_rules import validate_controller
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Controller", "controller.ts", validate_controller,
        "https://docs.erixcel.com/desarrollo/nestjs/src/modules-guia",
    ))
