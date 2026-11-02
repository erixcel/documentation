---
name: react-services
description: "Usar al crear o modificar servicios *.service.ts de frontend."
---

# react-services

## Fuente de verdad

- Documento: https://docs.erixcel.com/desarrollo/react/src/services
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/services.mdx
- Reglas de arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Consulta el MDX de esta página antes de realizar modificaciones relevantes; si no puedes acceder, indícalo y no inventes reglas.
2. Revisa los archivos y directorios afectados, incluso cambios de carpetas.
3. **En cualquier carpeta services/, solo archivos *.service.ts con imports y funciones al nivel superior. No clases, types/interfaces, estado global, JSX, ReactDOM ni hooks; no decorators NestJS.**
4. Conserva el comportamiento y los imports; utiliza TypeScript seguro sin reemplazar tipos con `any`.
5. Comprueba `npm run lint`, `npm run build` y las pruebas existentes cuando estén disponibles.

## Decisiones pendientes

El alcance de estado compartido se define en stores; la ubicación de contratos de tipos reutilizables sigue pendiente. No elimines cachés o sesiones. El Hook reporta cambios pero no corrige archivos por sí solo.

6. Accede a instancias existentes mediante funciones (`getApi`, `getAdminApi`, `getAdminSession`) importadas de stores. Evita nuevas instancias por llamada y ciclos con fábricas. Consulta `react-stores`.
