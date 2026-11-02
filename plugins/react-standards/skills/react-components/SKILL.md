---
name: react-components
description: "Usar al crear o modificar componentes compartidos React."
---

# react-components

## Fuente de verdad

- Documento: https://docs.erixcel.com/desarrollo/react/src/components
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/components.mdx
- Reglas de arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Consulta el MDX de esta página antes de realizar modificaciones relevantes; si no puedes acceder, indícalo y no inventes reglas.
2. Revisa los archivos y directorios afectados, incluso cambios de carpetas.
3. **Solo simple/ y complex/; simple contiene archivos planos *.component.tsx, complex requiere carpeta por componente con vista nombre.component.tsx y subcarpetas hooks/ y services/. No barrels.**
4. Conserva el comportamiento y los imports; utiliza TypeScript seguro sin reemplazar tipos con `any`.
5. Comprueba `npm run lint`, `npm run build` y las pruebas existentes cuando estén disponibles.

## Decisiones pendientes

La carpeta/sufijo definitivo de contratos de tipos y estado compartido aún no se acordó; **no improvises** una solución ni elimines cachés o sesiones. El Hook reporta cambios pero no corrige archivos por sí solo.
