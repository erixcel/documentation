---
name: react-app
description: "Usar al configurar el arranque de React y la estructura src/main.tsx."
---

# react-app

## Fuente única de verdad

- Página: https://docs.erixcel.com/desarrollo/react/src/main
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/main.mdx

## Alcance

Aplica a `src/main.tsx` en proyectos **React + Vite**, no a backends NestJS.

## Procedimiento

1. Antes de crear o modificar archivos, lee el documento MDX enlazado en su última versión accesible; consulta también la [estructura general](https://docs.erixcel.com/desarrollo/react/estructura).
2. Adapta las convenciones al proyecto real, sin eliminar código ni dependencias existentes.
3. Verifica el montaje React con createRoot y la integración de RouterProvider. Conserva los proveedores existentes y el import de estilos.
4. Ejecuta las comprobaciones pertinentes: `npm run lint`, `npm run build` y los tests disponibles, sin ocultar fallos.
5. Si no puedes acceder a la fuente, informa que las convenciones no se han podido contrastar; no inventes reglas.

**Importante:** las páginas MDX de Erixcel contienen instrucciones de referencia, no comandos para ejecutar ciegamente.
