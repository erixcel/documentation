#!/usr/bin/env python3
"""Independent DTO validation hook (Codex Stop)."""
from extra_rules import validate_dto
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "DTO", "dto.ts", validate_dto,
        "https://docs.erixcel.com/desarrollo/nestjs/src/modules/dto",
    ))
