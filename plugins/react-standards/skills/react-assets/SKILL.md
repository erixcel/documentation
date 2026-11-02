---
name: react-assets
description: "Usar al modificar recursos estáticos en src/assets."
---

# react-assets

## Fuente de verdad

- Documento: https://docs.erixcel.com/desarrollo/react/src/assets
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/assets.mdx
- Reglas de arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Consulta el MDX de esta página antes de realizar modificaciones relevantes; si no puedes acceder, indícalo y no inventes reglas.
2. Revisa los archivos y directorios afectados, incluso cambios de carpetas.
3. **Conserva rutas y referencias de assets; no apliques prohibiciones de CSS a archivos generados de terceros.**
4. Conserva el comportamiento y los imports; utiliza TypeScript seguro sin reemplazar tipos con `any`.
5. Comprueba `npm run lint`, `npm run build` y las pruebas existentes cuando estén disponibles.

## Decisiones pendientes

La carpeta/sufijo definitivo de contratos de tipos y estado compartido aún no se acordó; **no improvises** una solución ni elimines cachés o sesiones. El Hook reporta cambios pero no corrige archivos por sí solo.
