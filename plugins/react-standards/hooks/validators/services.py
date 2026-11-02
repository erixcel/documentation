"""Erixcel React hook validation; read-only."""
import re
from common.discovery import logic_files, text
from analyzers.ast import ast_check
from validators.api import validate_api

def validate_services(root, changed):
    issues, files = logic_files(root, changed, "services", ".service.ts")
    for name in files:
        if re.search(r"\bprocess\.env\b", text(root, name)):
            issues.append(f"{name}: usa import.meta.env en Vite, no process.env.")
    issues += ast_check(root, "services", files)
    return issues

def validate_api_services(root, changed):
    return validate_api(root, changed) + validate_services(root, changed)
