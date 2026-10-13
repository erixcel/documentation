"""Validate a single Query class at module scope (without TypeScript dependencies).

This is a lexical architecture check, not a replacement for the TypeScript compiler.
"""
import re

IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


def tokens(source):
    """Tokenize punctuation/identifiers while ignoring comments and string contents."""
    result = []
    n = len(source)
    i = 0
    line = 1
    previous = None
    while i < n:
        char = source[i]
        if char.isspace():
            if char == "\n":
                line += 1
            i += 1
            continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            i = n if end < 0 else end
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            end = n if end < 0 else end + 2
            line += source.count("\n", i, end)
            i = end
            continue
        if char in ('"', "'", chr(96)):
            start = i
            quote = char
            i += 1
            while i < n:
                if source[i] == "\\":
                    i += 2
                elif source[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            result.append(("STRING", line))
            line += source.count("\n", start, i)
            previous = "STRING"
            continue
        if char == "/" and previous in {"=", "(", "[", ":", ",", "return", "=>", "!"}:
            # Regex literals in initializers/methods may contain braces.
            j = i + 1
            inside_class = False
            closed = False
            while j < n and source[j] != "\n":
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == "[":
                    inside_class = True
                elif source[j] == "]":
                    inside_class = False
                elif source[j] == "/" and not inside_class:
                    closed = True
                    j += 1
                    while j < n and source[j].isalpha():
                        j += 1
                    break
                j += 1
            if closed:
                result.append(("REGEX", line))
                previous = "REGEX"
                i = j
                continue
        match = IDENTIFIER.match(source, i)
        if match:
            value = match.group(0)
            i = match.end()
        elif source.startswith("=>", i):
            value = "=>"
            i += 2
        else:
            value = char
            i += 1
        result.append((value, line))
        previous = value
    return result


def validate_one_class(source):
    """Only imports, class decorators and exactly one class at the top level."""
    all_tokens = tokens(source)
    i = 0
    classes = 0
    errors = []
    pending_decorator = False
    n = len(all_tokens)
    while i < n:
        word, line = all_tokens[i]
        if word == ";":
            i += 1
            continue
        if word == "import" and not pending_decorator:
            i += 1
            nesting = 0
            seen_module = False
            while i < n:
                value, _ = all_tokens[i]
                if value in ("{", "(", "["):
                    nesting += 1
                elif value in ("}", ")", "]"):
                    nesting -= 1
                elif value == "STRING" and nesting == 0:
                    seen_module = True
                if value == ";" and nesting == 0:
                    i += 1
                    break
                if seen_module and nesting == 0:
                    if i + 1 == n or (
                        all_tokens[i + 1][1] > all_tokens[i][1]
                        and all_tokens[i + 1][0] not in ("with", "assert")
                    ):
                        i += 1
                        break
                i += 1
            continue
        if word == "@":
            pending_decorator = True
            i += 1
            while i < n and (
                IDENTIFIER.fullmatch(all_tokens[i][0]) or all_tokens[i][0] == "."
            ):
                i += 1
            if i < n and all_tokens[i][0] == "(":
                depth = 0
                while i < n:
                    value = all_tokens[i][0]
                    if value == "(":
                        depth += 1
                    elif value == ")":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
            continue
        j = i
        if word == "export":
            j += 1
            while j < n and all_tokens[j][0] in ("default", "declare", "abstract"):
                j += 1
        elif word == "abstract":
            j += 1
        if j < n and all_tokens[j][0] == "class":
            classes += 1
            pending_decorator = False
            j += 1
            while j < n and all_tokens[j][0] != "{":
                j += 1
            if j >= n:
                errors.append(f"Línea {line}: declaración de clase sin cuerpo.")
                break
            depth = 0
            while j < n:
                value = all_tokens[j][0]
                if value == "{":
                    depth += 1
                elif value == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            if depth:
                errors.append(f"Línea {line}: clase con llaves desbalanceadas.")
                break
            i = j
            continue
        errors.append(
            f"Línea {line}: declaración '{word}' fuera de la clase. "
            "Un .query.ts solo puede contener imports, decoradores y una única clase. "
            "Mueve constantes y funciones al interior de la clase y ajusta sus referencias "
            "(por ejemplo, this.fields / this.visible), sin cambiar el comportamiento."
        )
        break
    if classes != 1 and not errors:
        errors.append(
            f"El archivo .query.ts debe declarar exactamente una clase (encontradas {classes})."
        )
    return errors
