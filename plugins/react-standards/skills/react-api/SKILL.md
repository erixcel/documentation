---
name: react-api
description: "Usar al modificar src/api/backend.api.ts generado."
---

# react-api

## Fuente de verdad

- Documento: https://docs.erixcel.com/desarrollo/react/src/api
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/api.mdx
- Reglas de arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Consulta el MDX de esta página antes de realizar modificaciones relevantes; si no puedes acceder, indícalo y no inventes reglas.
2. Revisa los archivos y directorios afectados, incluso cambios de carpetas.
3. **Solo backend.api.ts en src/api, sin carpetas ni otros archivos. No edites el generado manualmente; regenera el backend. El código generado puede contener types/interfaces/classes.**
4. Conserva el comportamiento y los imports; utiliza TypeScript seguro sin reemplazar tipos con `any`.
5. Comprueba `npm run lint`, `npm run build` y las pruebas existentes cuando estén disponibles.

## Decisiones pendientes

El alcance de estado compartido se define en stores; la ubicación de contratos de tipos reutilizables sigue pendiente. No elimines cachés o sesiones. El Hook reporta cambios pero no corrige archivos por sí solo.

6. Las instancias compartidas de API viven en stores; las operaciones, en servicios; y la integración React, en hooks. Consulta `react-stores`.
