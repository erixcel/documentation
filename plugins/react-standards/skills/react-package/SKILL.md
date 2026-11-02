---
name: react-package
description: "Usar al modificar dependencias y scripts de package.json en React + Vite."
---

# react-package

## Fuente única de verdad

- Página: https://docs.erixcel.com/desarrollo/react/package-json
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/package-json.mdx

## Alcance

Aplica a `package.json` en proyectos **React + Vite**, no a backends NestJS.

## Procedimiento

1. Antes de crear o modificar archivos, lee el documento MDX enlazado en su última versión accesible; consulta también la [estructura general](https://docs.erixcel.com/desarrollo/react/estructura).
2. Adapta las convenciones al proyecto real, sin eliminar código ni dependencias existentes.
3. Respeta los scripts dev, build, lint, preview y test y las dependencias de React 19, React Router 7, Tailwind 4 y Vite 8.
4. Ejecuta las comprobaciones pertinentes: `npm run lint`, `npm run build` y los tests disponibles, sin ocultar fallos.
5. Si no puedes acceder a la fuente, informa que las convenciones no se han podido contrastar; no inventes reglas.

**Importante:** las páginas MDX de Erixcel contienen instrucciones de referencia, no comandos para ejecutar ciegamente.
