"""Validaciones de módulos NestJS separadas por regla de arquitectura."""
import re
from validators._helpers import read, named_class


def validate_module(path):
    source, errors = read(path)
    if errors:
        return errors

    # Regla 1: El nombre de la clase y @Module deben corresponder al archivo.
    errors.extend(_validate_module_class(source, path))

    # Regla 2: @Module debe registrar sus dependencias mediante un objeto.
    errors.extend(_validate_module_metadata(source))

    # Regla 3: Un Module no puede contener consultas de base de datos.
    errors.extend(_validate_module_database_calls(source))

    # Regla 4: Archivos hermanos limitados a Module, Controller y Service.
    errors.extend(_validate_module_siblings(path))

    # Regla 5: Módulos y submódulos deben seguir la jerarquía modules/.
    errors.extend(_validate_module_hierarchy(path))

    # Regla 6: Submódulos hijos deben estar agrupados en modules/.
    errors.extend(_validate_module_child_directories(path))

    return errors


def _is_root_app_module(path):
    return path.name == "app.module.ts" and path.parent.name == "src"


def _validate_module_class(source, path):
    return named_class(source, path, ".module.ts", "Module", "Module")


def _validate_module_metadata(source):
    if not re.search(r"@Module\s*\(\s*\{", source):
        return ["@Module debe registrar las dependencias mediante un objeto."]
    return []


def _validate_module_database_calls(source):
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", source):
        return ["No coloques consultas de datos dentro de un módulo."]
    return []


def _validate_module_siblings(path):
    # Solo src/app.module.ts está exento de las reglas de archivos hermanos.
    if not path.name.endswith(".module.ts") or _is_root_app_module(path):
        return []

    base = path.name[:-len(".module.ts")]
    allowed = {base + ".module.ts", base + ".controller.ts", base + ".service.ts"}
    siblings = {
        item.name for item in path.parent.iterdir()
        if item.is_file() and item.name != ".DS_Store"
    }
    extra = sorted(siblings - allowed)
    if not extra:
        return []
    return [
        "Archivos hermanos no permitidos junto a " + path.name + ": "
        + ", ".join(extra)
        + ". Solo se admite el .module.ts y, cuando sean necesarios, "
          "su .controller.ts y .service.ts con idéntico nombre base. "
          "No crees Controller ni Service vacíos si no son necesarios. "
          "Las subcarpetas están permitidas. Usa functions/*.function.ts "
          "para utilidades estáticas sin inyección de dependencias. "
          "Un @Injectable() adicional puede requerir un submódulo "
          "con su propio .module.ts (Controller y Service opcionales). "
          "Antes de mover archivos, conserva imports, providers, exports "
          "y comportamiento."
    ]


def _validate_module_hierarchy(path):
    if not path.name.endswith(".module.ts") or _is_root_app_module(path):
        return []
    src = next((parent for parent in path.parents if parent.name == "src"), None)
    if src is None:
        return []

    errors = []
    stem = path.name[:-len(".module.ts")]
    if path.parent != src and path.parent.name != stem:
        errors.append(
            "La carpeta del módulo debe llamarse '" + stem +
            "' y contener " + stem + ".module.ts. "
            "No coloques archivos .module.ts directamente en modules/."
        )

    # Estructura estándar: src/modules/<main>/modules/<sub>/modules/<child>/...
    segments = path.relative_to(src).parts[:-1]
    if segments and segments[0] == "modules":
        if len(segments) == 1:
            errors.append(
                "Los módulos principales deben ir en "
                "src/modules/<nombre>/<nombre>.module.ts."
            )
        else:
            for position in range(2, len(segments), 2):
                if segments[position] != "modules":
                    suggested = (
                        src.joinpath(*segments[:position], "modules",
                                     *segments[position:], path.name)
                    )
                    errors.append(
                        "Submódulo fuera de la carpeta agrupadora modules/: "
                        + str(path) + ". Ruta esperada: "
                        + str(suggested) + ". Cada módulo agrupa sus "
                        "submódulos en modules/<nombre>/<nombre>.module.ts. "
                        "Al moverlo, actualiza imports, providers, exports, "
                        "rutas y tests sin modificar el comportamiento."
                    )
                    break
    else:
        # También cubre src/security/security.module.ts y similares.
        for ancestor in path.parent.parents:
            if ancestor == src:
                break
            if (ancestor / (ancestor.name + ".module.ts")).is_file():
                if path.relative_to(ancestor).parts[0] != "modules":
                    suggested = ancestor / "modules" / path.relative_to(ancestor)
                    errors.append(
                        "Submódulo fuera de modules/: " + str(path) +
                        ". Ruta esperada: " + str(suggested) +
                        ". Conserva las dependencias al reorganizar."
                    )
                    break
    return errors


def _validate_module_child_directories(path):
    if not path.name.endswith(".module.ts") or _is_root_app_module(path):
        return []
    src = next((parent for parent in path.parents if parent.name == "src"), None)
    if src is None:
        return []

    misplaced = []
    for child in path.parent.iterdir():
        if child.is_dir() and child.name != "modules":
            child_modules = sorted(
                candidate.name for candidate in child.glob("*.module.ts")
                if candidate.is_file()
            )
            if child_modules:
                misplaced.append(child.name + "/ (" + ", ".join(child_modules) + ")")
    if not misplaced:
        return []
    return [
        "Submódulos sueltos junto a " + path.name + ": "
        + ", ".join(misplaced)
        + ". Agrúpalos en modules/<nombre>/<nombre>.module.ts "
        "dentro del módulo actual. Las carpetas sin .module.ts "
        "(dto/, functions/, guards/, etc.) sí pueden permanecer "
        "como carpetas de responsabilidad. Conserva imports, "
        "providers, exports, rutas y tests al mover archivos."
    ]
