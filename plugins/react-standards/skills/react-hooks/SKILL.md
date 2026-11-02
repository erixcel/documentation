---
name: react-hooks
description: "Usar al crear o modificar hooks personalizados en React."
---

# react-hooks

## Fuente única de verdad

- Página: https://docs.erixcel.com/desarrollo/react/src/hooks
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/hooks.mdx

## Alcance

Aplica a `src/hooks/**` en proyectos **React + Vite**, no a backends NestJS.

## Procedimiento

1. Antes de crear o modificar archivos, lee el documento MDX enlazado en su última versión accesible; consulta también la [estructura general](https://docs.erixcel.com/desarrollo/react/estructura).
2. Adapta las convenciones al proyecto real, sin eliminar código ni dependencias existentes.
3. Respeta reglas de hooks de React, dependencias de efectos y limpieza de listeners; evita llamadas condicionales.
4. Ejecuta las comprobaciones pertinentes: `npm run lint`, `npm run build` y los tests disponibles, sin ocultar fallos.
5. Si no puedes acceder a la fuente, informa que las convenciones no se han podido contrastar; no inventes reglas.

**Importante:** las páginas MDX de Erixcel contienen instrucciones de referencia, no comandos para ejecutar ciegamente.
