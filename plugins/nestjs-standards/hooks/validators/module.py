"""Erixcel NestJS modular static hook validators; read-only."""
import json
import re
from pathlib import Path
from analyzers.query_structure import tokens
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT

def validate_module(path):
    s, errors = read(path)
    if errors:
        return errors
    errors += named_class(s, path, ".module.ts", "Module", "Module")
    if not re.search(r"@Module\s*\(\s*\{", s):
        errors.append("@Module debe registrar las dependencias mediante un objeto.")
    if re.search(r"\b(?:database|db)\s*\.\s*(?:select|insert|update|delete)\s*\(", s):
        errors.append("No coloques consultas de datos dentro de un módulo.")
    # Applies to every .module.ts in src, including src/security/.
    # Only the root src/app.module.ts is exempt from sibling conventions.
    # Controller and Service are optional but must share the module's base
    # name when present. Subdirectories are unrestricted.
    is_root_app_module = path.name == "app.module.ts" and path.parent.name == "src"
    if path.name.endswith(".module.ts") and not is_root_app_module:
        base = path.name[:-len(".module.ts")]
        allowed = {base + ".module.ts", base + ".controller.ts", base + ".service.ts"}
        siblings = {
            item.name for item in path.parent.iterdir()
            if item.is_file() and item.name != ".DS_Store"
        }
        extra = sorted(siblings - allowed)
        if extra:
            errors.append(
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
            )

    # A module's controller/service are optional; nested NestJS submodules
    # must be grouped in a dedicated 'modules/' child directory.
    if path.name.endswith(".module.ts") and not is_root_app_module:
        src = next((p for p in path.parents if p.name == "src"), None)
        if src is not None:
            stem = path.name[:-len(".module.ts")]
            if path.parent != src and path.parent.name != stem:
                errors.append(
                    "La carpeta del módulo debe llamarse '" + stem +
                    "' y contener " + stem + ".module.ts. "
                    "No coloques archivos .module.ts directamente en modules/."
                )

            # Standard NestJS feature tree:
            # src/modules/<main>/modules/<sub>/modules/<grandchild>/...
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
                # Also works for src/security/security.module.ts and other
                # non-feature modules: their descendants must use modules/.
                for ancestor in path.parent.parents:
                    if ancestor == src:
                        break
                    if (ancestor / (ancestor.name + ".module.ts")).is_file():
                        if path.relative_to(ancestor).parts[0] != "modules":
                            suggested = (
                                ancestor / "modules" /
                                path.relative_to(ancestor)
                            )
                            errors.append(
                                "Submódulo fuera de modules/: " + str(path) +
                                ". Ruta esperada: " + str(suggested) +
                                ". Conserva las dependencias al reorganizar."
                            )
                            break

            misplaced = []
            for child in path.parent.iterdir():
                if child.is_dir() and child.name != "modules":
                    child_modules = sorted(p.name for p in child.glob("*.module.ts")
                                           if p.is_file())
                    if child_modules:
                        misplaced.append(
                            child.name + "/ (" + ", ".join(child_modules) + ")"
                        )
            if misplaced:
                errors.append(
                    "Submódulos sueltos junto a " + path.name + ": " +
                    ", ".join(misplaced) +
                    ". Agrúpalos en modules/<nombre>/<nombre>.module.ts "
                    "dentro del módulo actual. Las carpetas sin .module.ts "
                    "(dto/, functions/, guards/, etc.) sí pueden permanecer "
                    "como carpetas de responsabilidad. Conserva imports, "
                    "providers, exports, rutas y tests al mover archivos."
                )
    return errors
