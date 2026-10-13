#!/usr/bin/env python3
"""Independent TSConfig validation hook (Codex Stop)."""
from extra_rules import validate_tsconfig
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "TSConfig", "tsconfig.json", validate_tsconfig,
        "https://docs.erixcel.com/desarrollo/nestjs/tsconfig",
    ))
