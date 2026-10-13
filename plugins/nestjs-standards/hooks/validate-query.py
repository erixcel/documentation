#!/usr/bin/env python3
"""Stop: validate changed *.query.ts using Erixcel architectural rules."""
import re
from pathlib import Path
from validator_common import run
from query_structure import validate_one_class

JOIN_RE = re.compile(r"\.\s*(?:leftJoin|rightJoin|innerJoin|fullJoin|crossJoin)\s*\(")
WRITE_RE = re.compile(r"\.\s*(?:insert|update|delete)\s*\(")
IMPORT_RE = re.compile(r"""(?m)^[ \t]*import\b[\s\S]*?\bfrom\s*['"]([^'"]+)['"]""")


def validate_query(path):
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"No se pudo leer: {exc}"]
    code = re.sub(r"/\*[\s\S]*?\*/|(?m:^[ \t]*//[^\n]*)", "", source)
    modules = [m.group(1) for m in IMPORT_RE.finditer(code)]
    tables = sorted(set(m for m in modules if m.endswith((".table", ".table.ts", ".table.js"))))
    issues = validate_one_class(content)
    if path.name.endswith("-join.query.ts"):
        for match in WRITE_RE.finditer(code):
            line = code.count("\n", 0, match.start()) + 1
            issues.append(f"Línea {line}: -join.query.ts es solo SELECT; no admite operaciones de escritura.")
    else:
        if len(tables) != 1:
            issues.append(f".query.ts debe importar solo una tabla *.table (encontradas {len(tables)}): {', '.join(tables) or 'ninguna'}.")
        for match in JOIN_RE.finditer(code):
            line = code.count("\n", 0, match.start()) + 1
            issues.append(f"Línea {line}: JOIN prohibido en .query.ts; utilice -join.query.ts.")
    return issues


if __name__ == "__main__":
    raise SystemExit(run(
        "Query", ".query.ts", validate_query,
        "https://docs.erixcel.com/desarrollo/nestjs/src/queries-guia",
    ))
