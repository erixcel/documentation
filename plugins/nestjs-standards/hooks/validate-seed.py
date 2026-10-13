#!/usr/bin/env python3
"""Independent Seed validation hook (Codex Stop)."""
from extra_rules import validate_seed
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Seed", "seed.ts", validate_seed,
        "https://docs.erixcel.com/desarrollo/nestjs/src/seeds-guia",
    ))
