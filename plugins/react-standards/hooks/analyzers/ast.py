"""Erixcel React hook validation; read-only."""
import json
import subprocess
from pathlib import Path

def ast_check(root, kind, paths):
    """TypeScript AST analysis via local TypeScript dependency; never modify files."""
    files = sorted(set(paths))
    if not files:
        return []
    script = Path(__file__).with_name("typescript-ast.mjs")
    try:
        result = subprocess.run(
            ["node", str(script), str(root), kind, *files],
            capture_output=True, text=True, timeout=25, check=False,
        )
        if result.returncode != 0:
            return [f"TypeScript AST: no se pudo completar el análisis de {kind}. "
                    "Comprueba Node.js y la instalación npm del frontend."]
        issues = json.loads(result.stdout)
        return [f"{err['file']}:{err['line']}: {err['rule']}" for err in issues]
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return ["TypeScript AST: fallo al analizar. Instala las dependencias y "
                "comprueba que Node.js/TypeScript estén disponibles."]
