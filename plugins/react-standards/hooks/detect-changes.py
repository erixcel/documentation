#!/usr/bin/env python3
"""Track frontend/src and config before Codex starts editing."""
import json
import sys
from validator_common import project_for, store

def main():
    try:
        payload = json.load(sys.stdin)
        if payload.get("hook_event_name") != "UserPromptSubmit":
            print("{}")
            return 0
        project = project_for(payload)
        if project is not None:
            store(payload, project)
        print("{}")
    except Exception as exc:
        print(json.dumps({"systemMessage": "Erixcel React: no se pudo registrar snapshot (" + type(exc).__name__ + ")."}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
