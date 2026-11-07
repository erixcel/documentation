"""Reglas de estilos Tailwind y AST para proyectos Erixcel React."""
import re
from common.constants import SKIP
from analyzers.ast import ast_check


def validate_styles(root, changed):
    issues = []
    style_changes = any(
        name.startswith("src/") and name.endswith((".css", ".scss", ".sass", ".less"))
        for name in changed
    )
    tsx_changes = [
        name for name in changed
        if name.startswith("src/") and name.endswith(".tsx") and (root / name).is_file()
    ]
    if not style_changes and not tsx_changes:
        return issues

    # Regla 1: Prohibir archivos de estilo adicionales a src/index.css.
    issues.extend(_validate_styles_no_external_css(root))

    # Regla 2: index.css solo admite Tailwind y bloques @theme con tokens.
    if style_changes:
        issues.extend(_validate_styles_index_css(root))

    # Regla 3: El AST revisa estilos inline en archivos TSX cambiados.
    issues.extend(_validate_styles_ast(root, tsx_changes))

    return issues


def _validate_styles_no_external_css(root):
    issues = []
    forbidden = (".css", ".scss", ".sass", ".less")
    for path in (root / "src").rglob("*"):
        if not path.is_file() or path.is_symlink() or any(p in SKIP for p in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.endswith(forbidden) and rel != "src/index.css":
            issues.append(
                f"{rel}: CSS propio prohibido; utiliza className con Tailwind en lugar de CSS externo."
            )
    return issues


def _validate_styles_index_css(root):
    css = root / "src/index.css"
    if not css.is_file():
        return []

    issues = []
    data = css.read_text(encoding="utf-8")
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", data).strip()
    imp = re.match(r"@import\s+['\"]tailwindcss['\"]\s*;", cleaned)
    if not imp:
        issues.append("src/index.css:1: el archivo debe comenzar con @import 'tailwindcss';.")
    else:
        rest = cleaned[imp.end():].strip()
        while rest:
            match = re.match(r"@theme(?:\s+(?:inline|static|default))?\s*\{", rest)
            if not match:
                issues.append(
                    "src/index.css: solo se permiten @import 'tailwindcss'; y bloques @theme. "
                    "Prohibidos selectores, @apply, @layer, @media y @keyframes."
                )
                break
            depth = 1
            end = match.end()
            while end < len(rest) and depth:
                if rest[end] == "{":
                    depth += 1
                elif rest[end] == "}":
                    depth -= 1
                end += 1
            if depth:
                issues.append("src/index.css: bloque @theme sin cierre.")
                break
            body = rest[match.end():end - 1].strip()
            tokens = re.findall(r"--[A-Za-z0-9_-]+\s*:\s*[^;{}]+;", body)
            if re.sub(r"--[A-Za-z0-9_-]+\s*:\s*[^;{}]+;", "", body).strip():
                issues.append("src/index.css: @theme solo puede contener tokens CSS (--nombre: valor;).")
            rest = rest[end:].strip()
    return issues


def _validate_styles_ast(root, tsx_changes):
    return ast_check(root, "styles", tsx_changes)
