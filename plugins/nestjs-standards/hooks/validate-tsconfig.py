#!/usr/bin/env python3
"""Independent TSConfig validation hook (Codex Stop)."""
from validators.tsconfig import validate_tsconfig
from common.runner import run

if __name__ == "__main__":
    raise SystemExit(run(
        "TSConfig", "tsconfig.json", validate_tsconfig,
        "https://docs.erixcel.com/desarrollo/nestjs/tsconfig",
    ))
