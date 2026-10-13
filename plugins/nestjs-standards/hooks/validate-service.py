#!/usr/bin/env python3
"""Independent Service validation hook (Codex Stop)."""
from extra_rules import validate_service
from validator_common import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Service", "service.ts", validate_service,
        "https://docs.erixcel.com/desarrollo/nestjs/src/modules-guia",
    ))
