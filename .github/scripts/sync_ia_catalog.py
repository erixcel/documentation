#!/usr/bin/env python3
"""Generate Mintlify IA catalogs from the Codex plugin marketplace."""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_URL = "https://github.com/erixcel/documentation/blob/main"


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


def render_cards(items, icon):
    if not items:
        return "No hay elementos publicados de este tipo.\n"
    cards = []
    for item in items:
        cards.append(
            f'<Card title="{safe_attr(item["title"])}" icon="{icon}" href="{safe_attr(item["url"])}">\n'
            f'{safe_text(item["description"])}\n'
            "</Card>"
        )
    return "<Columns cols={1}>\n" + "\n".join(cards) + "\n</Columns>\n"


def generate():
    skills = []
    hooks = []
    for plugin in load_plugins():
        root = plugin["root"]
        for path in sorted((root / "skills").rglob("SKILL.md")):
            data = skill_metadata(path)
            skills.append({
                "title": data["name"],
                "description": f'{plugin["name"]} (v{plugin["version"]}) · {data["description"]}',
                "url": f'{REPO_URL}/{path.relative_to(ROOT).as_posix()}',
            })
        file = root / "hooks/hooks.json"
        if file.exists():
            config = json.loads(file.read_text(encoding="utf-8"))
            for event, registrations in (config.get("hooks") or {}).items():
                for block in registrations:
                    for hook in block.get("hooks", []):
                        title = hook.get("statusMessage") or f'{event} · {hook.get("type", "hook")}'
                        hooks.append({
                            "title": title,
                            "description": f'{plugin["name"]} (v{plugin["version"]}) · Evento {event}. Tipo: {hook.get("type", "command")}.',
                            "url": f'{REPO_URL}/{file.relative_to(ROOT).as_posix()}',
                        })
    skill_page = f'''---
title: "Skills"
sidebarTitle: "Skills"
---

Las **Skills de Erixcel** son instrucciones reutilizables para agentes de programación. Este catálogo se genera a partir de los archivos `SKILL.md` de los plugins registrados en [Erixcel Developer Tools]({REPO_URL}/.agents/plugins/marketplace.json).

## Cómo instalarlas

<Steps>
  <Step title="Agregar el marketplace">
    Abre **Codex Desktop → Customize → Plugins → Add → Add a marketplace** y pega lo siguiente en **Source**:

    ```text Marketplace de Erixcel
    erixcel/documentation
    ```
  </Step>

  <Step title="Instalar Erixcel NestJS">
    En la pestaña **Personal**, busca **Erixcel Developer Tools** e instala **Erixcel NestJS**, que contiene las ocho Skills.
  </Step>

  <Step title="Comprobar las Skills">
    Entra a **Codex Desktop → Customize → Skills** y confirma que aparezcan las ocho Skills.
  </Step>

  <Step title="Utilizarlas">
    Abre tu proyecto NestJS y solicita, por ejemplo: «Usa la Skill `nestjs-core` para revisar `cors.core.ts` y consulta primero la documentación de Erixcel».
  </Step>
</Steps>

<Note>
Aquí se muestran **Skills publicadas en GitHub**, no necesariamente instaladas en tu equipo. Para comprobar las Skills realmente instaladas, abre **Codex Desktop → Customize → Skills** o revisa los plugins instalados.
</Note>

## Skills disponibles ({len(skills)})

{render_cards(skills, "book-open")}

## Actualizaciones

Las instrucciones de cada Skill siguen teniendo su fuente original en GitHub. Si cambia un `SKILL.md`, este catálogo se regenera automáticamente en el repositorio; actualizar la instalación local del plugin sigue siendo un proceso independiente.
'''
    hook_page = f'''---
title: "Hooks"
sidebarTitle: "Hooks"
---

Los **Hooks de Erixcel** ejecutan tareas durante eventos del ciclo de trabajo de Codex. Este catálogo se obtiene de los archivos `hooks/hooks.json` de los plugins registrados en [Erixcel Developer Tools]({REPO_URL}/.agents/plugins/marketplace.json).

## Cómo instalarlos y activarlos

<Steps>
  <Step title="Agregar el marketplace">
    Abre **Codex Desktop → Customize → Plugins → Add → Add a marketplace** y pega lo siguiente en **Source**, si todavía no agregaste el repositorio:

    ```text Marketplace de Erixcel
    erixcel/documentation
    ```
  </Step>

  <Step title="Instalar un plugin con Hooks">
    En **Personal**, instala el plugin que contenga el Hook que necesites. Actualmente no hay Hooks publicados en el catálogo de Erixcel.
  </Step>

  <Step title="Revisar los Hooks">
    Abre **Codex Desktop → Settings → Hooks** y verifica los Hooks detectados desde tus plugins o proyectos.
  </Step>

  <Step title="Autorizar y activar">
    Inspecciona el comando que ejecutará cada Hook, presiona **Trust** solo si confías en él y activa su interruptor.
  </Step>

  <Step title="Probar la ejecución">
    Realiza una interacción que desencadene el evento configurado (por ejemplo, **Stop**) y comprueba el resultado o el registro del Hook.
  </Step>
</Steps>

<Warning>
Este listado muestra **Hooks publicados en GitHub**, no cuáles están autorizados, activos o instalados en tu Mac. Consulta **Codex Desktop → Settings → Hooks** para ver el estado real. Los hooks pueden ejecutar comandos fuera del sandbox: revisa su contenido antes de autorizarlos.
</Warning>

## Hooks disponibles ({len(hooks)})

{render_cards(hooks, "workflow")}

## Sincronización

Los Hooks pueden agruparse en plugins y distribuirse desde GitHub. El catálogo se sincroniza automáticamente con su configuración versionada, **no** con el estado de ejecución local.
'''
    for name, content in [("skills", skill_page), ("hooks", hook_page)]:
        output = ROOT / "ia" / f"{name}.mdx"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    print(f"Generated: {len(skills)} skills and {len(hooks)} hooks")


if __name__ == "__main__":
    generate()
