---
name: react-pages
description: "Usar al crear páginas React agrupadas por funcionalidad."
---

# react-pages

## Fuente de verdad

- Documento: https://docs.erixcel.com/desarrollo/react/src/pages
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/pages.mdx
- Reglas de arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Consulta el MDX de esta página antes de realizar modificaciones relevantes; si no puedes acceder, indícalo y no inventes reglas.
2. Revisa los archivos y directorios afectados, incluso cambios de carpetas.
3. **Agrupa funcionalidades en src/pages/nombre/, permite index.ts públicos de páginas y coloca not-found en src/pages/not-found; no NestJS.**
4. Conserva el comportamiento y los imports; utiliza TypeScript seguro sin reemplazar tipos con `any`.
5. Comprueba `npm run lint`, `npm run build` y las pruebas existentes cuando estén disponibles.

## Decisiones pendientes

El alcance de estado compartido se define en stores; la ubicación de contratos de tipos reutilizables sigue pendiente. No elimines cachés o sesiones. El Hook reporta cambios pero no corrige archivos por sí solo.

6. Mantén los stores compartidos entre subpáginas dentro de `src/pages/<sección>/stores/` y globaliza solo si los usan distintas páginas principales. No crees stores vacíos.
