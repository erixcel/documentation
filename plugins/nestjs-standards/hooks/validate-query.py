#!/usr/bin/env python3
"""Erixcel NestJS Query Stop hook: thin entry point."""
from common.runner import run
from validators.query import validate_query

if __name__ == "__main__":
    raise SystemExit(run(
        "Query", ".query.ts", validate_query,
        "https://docs.erixcel.com/desarrollo/nestjs/src/queries-guia",
    ))
