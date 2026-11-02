#!/usr/bin/env python3
"""Independent Controller validation hook (Codex Stop)."""
from validators.controller import validate_controller
from common.runner import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Controller", "controller.ts", validate_controller,
        "https://docs.erixcel.com/desarrollo/nestjs/src/modules-guia",
    ))
