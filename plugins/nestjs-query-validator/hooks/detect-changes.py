#!/usr/bin/env python3
"""UserPromptSubmit: snapshot Query and Core files at the start of the turn."""
import json
import sys
from validator_common import workspace_for, store_snapshot


def main():
    try:
        payload = json.load(sys.stdin)
        if payload.get("hook_event_name") != "UserPromptSubmit":
            print("{}")
            return 0
        root = workspace_for(payload)
        if root is None:
            print(json.dumps({"systemMessage": "Erixcel: no hay carpeta de proyecto para crear el snapshot."}))
            return 0
        store_snapshot(payload, root)
        print("{}")
    except Exception as exc:
        print(json.dumps({"systemMessage": "Erixcel: error al registrar cambios (" + type(exc).__name__ + ")."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
