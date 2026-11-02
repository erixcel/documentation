#!/usr/bin/env python3
"""Generate Mintlify IA catalogs from the Codex plugin marketplace."""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_URL = "https://github.com/erixcel/documentation/blob/main"

SKILL_CARD_DETAILS = {
    "nestjs-core": {
        "description": "Configura archivos `.core.ts` y su integración con `main.ts`."
    },
    "nestjs-db": {
        "description": "Organiza PostgreSQL, Drizzle y las operaciones de base de datos."
    },
    "nestjs-functions": {
        "description": "Define utilidades reutilizables en archivos `.function.ts`."
    },
    "nestjs-global-dto": {
        "description": "Define los DTO compartidos por diferentes módulos."
    },
    "nestjs-module-dto": {
        "description": "Define los DTO de entrada, filtros y salida de cada módulo."
    },
    "nestjs-modules": {
        "description": "Organiza controllers, services y módulos de NestJS."
    },
    "nestjs-scripts": {
        "description": "Organiza scripts y generadores de automatización."
    },
    "nestjs-tsconfig": {
        "description": "Configura `tsconfig.json` y los alias de TypeScript."
    },
    "react-app": {"description": "Inicializa React en `src/main.tsx` y conecta RouterProvider."},
    "react-api": {"description": "Organiza clientes HTTP y contratos bajo `src/api/`."},
    "react-assets": {"description": "Gestiona imágenes y recursos estáticos de `src/assets/`."},
    "react-components": {"description": "Construye componentes reutilizables en `src/components/`."},
    "react-functions": {"description": "Ubica funciones TypeScript compartidas con sufijo `.function.ts`."},
    "react-interfaces": {"description": "Organiza contratos de frontend `.interface.ts` por ámbito."},
    "react-layouts": {"description": "Separa vistas grandes en secciones `.layout.tsx`, sin páginas internas."},
    "react-hooks": {"description": "Define hooks personalizados `useXxx` en `src/hooks/`."},
    "react-pages": {"description": "Agrupa las páginas del frontend por funcionalidad en `src/pages/`."},
    "react-routes": {"description": "Organiza las rutas y navegación desde `src/routes/`."},
    "react-services": {"description": "Separa las operaciones en servicios y reutiliza instancias de stores."},
    "react-stores": {"description": "Conserva sesiones, clientes y cachés en `*.store.ts`, globales o por sección."},
    "react-env": {"description": "Documenta y valida las variables `.env` y `.env.example`."},
    "react-package": {"description": "Mantiene los scripts y dependencias de `package.json`."}
}



def safe_text(value):
    value = " ".join(str(value).split())
    return html.escape(value, quote=False).replace("{", "&#123;").replace("}", "&#125;")


def safe_attr(value):
    return html.escape(str(value), quote=True).replace("{", "&#123;").replace("}", "&#125;")


def skill_metadata(path):
    source = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", source, re.DOTALL)
    data = {}
    if not match:
        return {"name": path.parent.name, "description": "Skill sin descripción."}
    lines = match.group(1).splitlines()
    for i, line in enumerate(lines):
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        if key not in ("name", "description"):
            continue
        value = value.strip().strip("\"'")
        if value in ("|", "|-", ">", ">-"):
            following = []
            for candidate in lines[i + 1 :]:
                if candidate and not candidate[0].isspace():
                    break
                following.append(candidate.strip())
            value = " ".join(following)
        data[key] = value
    return {
        "name": data.get("name") or path.parent.name,
        "description": data.get("description") or "Sin descripción.",
    }


def load_plugins():
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    plugins = []
    for record in marketplace.get("plugins", []):
        source = record.get("source") or {}
        if source.get("source") != "local" or not source.get("path"):
            continue
        root = (ROOT / source["path"]).resolve()
        # Never traverse paths outside this repository.
        if not root.is_relative_to(ROOT.resolve()) or not root.is_dir():
            continue
        manifest_path = root / ".codex-plugin/plugin.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        plugins.append({
            "root": root,
            "name": manifest.get("interface", {}).get("displayName") or manifest.get("name") or root.name,
            "version": manifest.get("version") or "sin versión",
        })
    return sorted(plugins, key=lambda x: x["name"].lower())


def render_cards(items, icon, horizontal=False):
    if not items:
        return "No hay elementos publicados de este tipo.\n"
    cards = []
    layout = " horizontal" if horizontal else ""
    for item in items:
        cards.append(
            f'<Card title="{safe_attr(item["title"])}" icon="{safe_attr(icon)}" href="{safe_attr(item["url"])}"{layout}>\n'
            f'{safe_text(item["description"])}\n'
            "</Card>"
        )
    return "<Columns cols={1}>\n" + "\n".join(cards) + "\n</Columns>\n"

def hook_filename(command):
    """Extract the source script name for the lifecycle tree."""
    match = re.search(r"([\w-]+\.(?:py|js|ts|sh))\b", command or "")
    return match.group(1) if match else "hook"


HOOK_DESCRIPTIONS = {
    "detect-changes.py": "Registra el estado inicial de todos los archivos NestJS vigilados.",
    "validate-functions.py": "Comprueba funciones React `.function.ts` sin clases ni decoradores NestJS.",
    "validate-page-files.py": "Comprueba una vista `.page.tsx` por página y subpágina.",
    "validate-interfaces.py": "Comprueba sufijos `.interface.ts` de contratos React.",
    "validate-layouts.py": "Comprueba vistas `.layout.tsx` y prohíbe `pages/` dentro de layouts.",
    "validate-query.py": "Una clase por `.query.ts`; separa consultas simples y JOIN.",
    "validate-core.py": "Valida las funciones setup de `.core.ts` y su integración.",
    "validate-controller.py": "Valida `.controller.ts`: decoradores HTTP, Swagger y delegación al Service.",
    "validate-service.py": "Valida `.service.ts`: servicios Injectable y consultas mediante Queries.",
    "validate-module.py": "Valida `.module.ts`: archivos hermanos y submódulos agrupados en `modules/`; solo `app.module.ts` exceptuado.",
    "validate-dto.py": "Valida `.dto.ts`: contratos, trazabilidad y separación de capas.",
    "validate-function.py": "Valida `.function.ts`: una clase sin types/interfaces sueltos; métodos static con `@TraceNode`.",
    "validate-table.py": "Valida `.table.ts`: tablas Drizzle y tres campos de auditoría.",
    "validate-seed.py": "Valida `src/seeds/`: solo `*.seed.ts` sin subcarpetas, una función por archivo y datos integrados.",
    "validate-script.py": "Valida `scripts/*.ts`: nombres, secretos y rutas locales fijas.",
    "validate-tsconfig.py": "Valida `tsconfig.json`: JSONC, módulo NodeNext y alias de TypeScript."
}


REACT_HOOK_DESCRIPTIONS = {
    "detect-changes.py": "Registra el estado de `src/`, `package.json` y `.env` antes de editar.",
    "validate-main.py": "Revisa `main.tsx`, RouterProvider y carga de estilos.",
    "validate-styles.py": "Solo `index.css` con Tailwind y tokens `@theme`; sin CSS propio adicional.",
    "validate-api.py": "Exige únicamente `src/api/backend.api.ts` autogenerado.",
    "validate-components.py": "Comprueba componentes `simple/` y `complex/` y sus convenciones.",
    "validate-hooks.py": "Exige `*.hook.ts`: solo imports y funciones (AST de TypeScript).",
    "validate-services.py": "Exige `*.service.ts`: solo funciones, sin JSX ni React Hooks.",
    "validate-stores.py": "Valida `*.store.ts`: rutas, nombres y ausencia de JSX o React Hooks (AST).",
    "validate-env.py": "Comprueba `.env` y `.env.example` sin exponer secretos.",
}


def describe_hook(item):
    filename = hook_filename(item["command"])
    if item.get("plugin") == "Erixcel React":
        return REACT_HOOK_DESCRIPTIONS.get(filename, "Validación de React + Vite.")
    return HOOK_DESCRIPTIONS.get(filename, f'Hook del evento {item["event"]}.')


def render_hook_groups(items):
    if not items:
        return "No hay Hooks publicados por ahora.\n"

    groups = {}
    for item in items:
        groups.setdefault(item["event"], []).append(item)

    priority = {"UserPromptSubmit": 0, "Stop": 1}
    parts = []
    for event in sorted(groups, key=lambda value: (priority.get(value, 2), value)):
        entries = groups[event]
        label = {"UserPromptSubmit": "Antes de comenzar", "Stop": "Al terminar"}.get(event, "Evento")
        intro = {
            "UserPromptSubmit": "Evento **`UserPromptSubmit`**: registra el estado inicial de los archivos al enviar tu mensaje.",
            "Stop": "Evento **`Stop`**: revisa los archivos modificados cuando Codex termina.",
        }.get(event, "Hooks registrados para este evento de Codex.")
        cards = render_cards([
            {
                "title": item["title"].removesuffix(" - Erixcel React").removesuffix(" - Erixcel"),
                "description": describe_hook(item),
                "url": item["url"],
            } for item in entries
        ], "shield-check", horizontal=True)
        parts.append(f'### {label}\n\n{intro}\n\n{cards}')
    return "\n\n".join(parts)

PLUGIN_CATALOGS = {
    "nestjs-standards": ("nestjs", "NestJS"),
    "react-standards": ("react", "React"),
}


def generate():
    """Keep each plugin's Skill and Hook catalog independent."""
    discovered = load_plugins()
    summaries = []
    for plugin in discovered:
        key = plugin["root"].name
        if key not in PLUGIN_CATALOGS:
            continue
        slug, label = PLUGIN_CATALOGS[key]
        root = plugin["root"]
        skills = []
        hooks = []

        for path in sorted((root / "skills").rglob("SKILL.md")):
            data = skill_metadata(path)
            presentation = SKILL_CARD_DETAILS.get(data["name"], {})
            skills.append({
                "title": data["name"],
                "description": presentation.get("description") or data["description"],
                "url": f'{REPO_URL}/{path.relative_to(ROOT).as_posix()}',
            })

        config_path = root / "hooks/hooks.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            for event, registrations in (config.get("hooks") or {}).items():
                for block in registrations:
                    for hook in block.get("hooks", []):
                        hooks.append({
                            "title": hook.get("statusMessage") or f'{event} · {hook.get("type", "hook")}',
                            "plugin": plugin["name"],
                            "event": event,
                            "command": hook.get("command") or "",
                            "url": f'{REPO_URL}/{config_path.relative_to(ROOT).as_posix()}',
                        })

        intro = (
            f"Este catálogo contiene **únicamente las Skills del plugin Erixcel {label}**. "
            f"Se genera a partir de sus archivos SKILL.md en GitHub; no incluye Skills de otros plugins."
        )
        skill_page = f'''---
title: "Skills de {label}"
sidebarTitle: "Skills"
---

{intro}

Antes de usarlas, consulta la [guía de instalación de Erixcel {label}](/ia/{slug}).
Instala solo el plugin que corresponda a tu proyecto desde [Erixcel Developer Tools]({REPO_URL}/.agents/plugins/marketplace.json).

## Skills disponibles ({len(skills)})

{render_cards(skills, "book-open", horizontal=True)}

## Sincronización

El catálogo representa los archivos publicados en GitHub. Actualizar el plugin instalado en Codex Desktop es un paso independiente.
'''
        hook_page = f'''---
title: "Hooks de {label}"
sidebarTitle: "Hooks"
---

Los siguientes Hooks pertenecen **exclusivamente a Erixcel {label}**.
No se mezclan con los validadores del otro plugin. Para instalarlos y activarlos, sigue la [guía de Erixcel {label}](/ia/{slug}).

## Hooks por evento ({len(hooks)})

{render_hook_groups(hooks)}

## Activación

Abre **Codex Desktop → Settings → Hooks**. Revisa los comandos de Erixcel {label}, pulsa **Trust** solo si confías en ellos y activa sus interruptores.
Los Hooks publicados en GitHub no reflejan si están activados en tu equipo.

## Sincronización

Este listado se genera desde el archivo de Hooks del plugin en GitHub; no desde los Hooks instalados localmente.
'''
        dest = ROOT / "ia" / slug
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "skills.mdx").write_text(skill_page, encoding="utf-8")
        (dest / "hooks.mdx").write_text(hook_page, encoding="utf-8")
        summaries.append((label, slug, len(skills), len(hooks)))

    # Keep former /ia/skills and /ia/hooks links useful without combining lists.
    for category in ("skills", "hooks"):
        title = "Skills" if category == "skills" else "Hooks"
        links = "\n".join(
            f'<Card title="Erixcel {label}" icon="{"book-open" if category == "skills" else "shield-check"}" '
            f'href="/ia/{slug}/{category}" horizontal>'
            f'Ver solo los {title} de {label}.</Card>'
            for label, slug, _, _ in summaries
        )
        content = (
            f'---\ntitle: "{title}"\nsidebarTitle: "{title}"\n---\n\n'
            f'# {title} por plugin\n\n'
            f'Selecciona un plugin para consultar sus {title} sin mezclar tecnologías.\n\n'
            f'<Columns cols={1}>\n{links}\n</Columns>\n'
        )
        (ROOT / "ia" / f"{category}.mdx").write_text(content, encoding="utf-8")

    for label, slug, nskills, nhooks in summaries:
        print(f"Generated Erixcel {label}: {nskills} Skills and {nhooks} Hooks")


if __name__ == "__main__":
    generate()
