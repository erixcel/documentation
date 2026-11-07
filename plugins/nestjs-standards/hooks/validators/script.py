"""Valida scripts NestJS mediante reglas independientes y de solo lectura."""
import re
from validators._helpers import read


def validate_script(path):
    source, errors = read(path)
    if errors:
        return errors

    # Regla 1: El nombre del script debe usar kebab-case y terminar en .ts.
    errors.extend(_validate_script_filename(path))

    # Regla 2: No se permiten credenciales incrustadas en el código.
    errors.extend(_validate_script_credentials(source))

    # Regla 3: No se permiten rutas absolutas ligadas a otra máquina.
    errors.extend(_validate_script_absolute_paths(source))

    return errors


def _validate_script_filename(path):
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.ts", path.name):
        return ["Los scripts usan nombres descriptivos kebab-case terminados en .ts."]
    return []


def _validate_script_credentials(source):
    if re.search(r"(?i)\b(?:password|api_?key|secret|access_?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", source):
        return ["Posible credencial incrustada en script: usa variables de entorno."]
    return []


def _validate_script_absolute_paths(source):
    if re.search(r"['\"]/(?:Users|home)/[^'\"]+['\"]", source):
        return ["No uses rutas absolutas de otra máquina: resuélvelas desde el proyecto."]
    return []
