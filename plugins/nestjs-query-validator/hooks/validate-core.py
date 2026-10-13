#!/usr/bin/env python3
"""Stop: validate changed *.core.ts using Erixcel architectural rules."""
from core_validator import validate_core
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Core", ".core.ts", validate_core,
        "https://docs.erixcel.com/desarrollo/nestjs/src/core/index",
    ))
