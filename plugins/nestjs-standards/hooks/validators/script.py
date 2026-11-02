"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

def validate_script(path):
    s, errors = read(path)
    if errors:
        return errors
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.ts", path.name):
        errors.append("Los scripts usan nombres descriptivos kebab-case terminados en .ts.")
    if re.search(r"(?i)\b(?:password|api_?key|secret|access_?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", s):
        errors.append("Posible credencial incrustada en script: usa variables de entorno.")
    if re.search(r"['\"]/(?:Users|home)/[^'\"]+['\"]", s):
        errors.append("No uses rutas absolutas de otra máquina: resuélvelas desde el proyecto.")
    return errors
