---
name: react-layouts
description: "Usar al crear o modificar Secciones internas de una página React siguiendo la arquitectura Erixcel React."
---

# react-layouts

## Fuente de verdad

- https://docs.erixcel.com/desarrollo/react/src/pages
- https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Examina la página y sus consumidores antes de crear un recurso. Elige siempre el ancestro común más cercano, no el ámbito global por comodidad.
2. Coloca el recurso en `layout/` dentro de la página, subpágina o en `src/` si lo comparten páginas principales. Respeta el sufijo `*.layout.tsx`.
3. No dupliques archivos ni uses index.ts para exponer recursos privados; mueve el original y actualiza los imports.
4. Los layouts son secciones de una misma página grande: layout/<sección>/<sección>.layout.tsx. Nunca introduzcas pages/ dentro de layout/; coloca subpáginas en pages/ de su página padre.
5. Comprueba el Hook correspondiente, npm run lint, npm run build y las pruebas disponibles. Los Hooks no modifican archivos automáticamente.
