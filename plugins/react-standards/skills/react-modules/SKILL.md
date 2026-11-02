---
name: react-modules
description: "Usar al crear funcionalidades y agrupar módulos React."
---

# react-modules

## Fuente única de verdad

- Página: https://docs.erixcel.com/desarrollo/react/src/modules
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/modules.mdx

## Alcance

Aplica a `src/modules/**` en proyectos **React + Vite**, no a backends NestJS.

## Procedimiento

1. Antes de crear o modificar archivos, lee el documento MDX enlazado en su última versión accesible; consulta también la [estructura general](https://docs.erixcel.com/desarrollo/react/estructura).
2. Adapta las convenciones al proyecto real, sin eliminar código ni dependencias existentes.
3. Agrupa funcionalidades por carpeta de dominio. Sus componentes, servicios, hooks y rutas pueden vivir dentro del módulo.
4. Ejecuta las comprobaciones pertinentes: `npm run lint`, `npm run build` y los tests disponibles, sin ocultar fallos.
5. Si no puedes acceder a la fuente, informa que las convenciones no se han podido contrastar; no inventes reglas.

**Importante:** las páginas MDX de Erixcel contienen instrucciones de referencia, no comandos para ejecutar ciegamente.
