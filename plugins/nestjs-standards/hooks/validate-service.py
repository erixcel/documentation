#!/usr/bin/env python3
"""Independent Service validation hook (Codex Stop)."""
from validators.service import validate_service
from common.runner import run

if __name__ == "__main__":
    raise SystemExit(run(
        "Service", "service.ts", validate_service,
        "https://docs.erixcel.com/desarrollo/nestjs/src/modules-guia",
    ))
