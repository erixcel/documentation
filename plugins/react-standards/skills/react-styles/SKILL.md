---
name: react-styles
description: "Usar al modificar Tailwind, className o src/index.css."
---

# react-styles

## Fuente de verdad

- Documento: https://docs.erixcel.com/desarrollo/react/src/styles
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/styles.mdx
- Reglas de arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Consulta el MDX de esta página antes de realizar modificaciones relevantes; si no puedes acceder, indícalo y no inventes reglas.
2. Revisa los archivos y directorios afectados, incluso cambios de carpetas.
3. **Único CSS propio src/index.css con import tailwindcss y tokens @theme; sin selectores CSS, otros CSS, style tags ni CSS-in-JS. Usa className de Tailwind.**
4. Conserva el comportamiento y los imports; utiliza TypeScript seguro sin reemplazar tipos con `any`.
5. Comprueba `npm run lint`, `npm run build` y las pruebas existentes cuando estén disponibles.

## Decisiones pendientes

La carpeta/sufijo definitivo de contratos de tipos y estado compartido aún no se acordó; **no improvises** una solución ni elimines cachés o sesiones. El Hook reporta cambios pero no corrige archivos por sí solo.
