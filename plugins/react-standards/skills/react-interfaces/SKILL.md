---
name: react-interfaces
description: "Usar al crear o modificar Interfaces React siguiendo la arquitectura Erixcel React."
---

# react-interfaces

## Fuente de verdad

- https://docs.erixcel.com/desarrollo/react/src/pages
- https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Examina la página y sus consumidores antes de crear un recurso. Elige siempre el ancestro común más cercano, no el ámbito global por comodidad.
2. Coloca el recurso en `interface/` dentro de la página, subpágina o en `src/` si lo comparten páginas principales. Respeta el sufijo `*.interface.ts`.
3. No dupliques archivos ni uses index.ts para exponer recursos privados; mueve el original y actualiza los imports.
4. No uses clases ni decoradores NestJS en funciones de frontend. Mantén contratos TypeScript y recursos sin carpetas vacías.
5. Comprueba el Hook correspondiente, npm run lint, npm run build y las pruebas disponibles. Los Hooks no modifican archivos automáticamente.
