---
name: react-hooks
description: "Usar al crear o modificar hooks personalizados *.hook.ts."
---

# react-hooks

## Fuente de verdad

- Documento: https://docs.erixcel.com/desarrollo/react/src/hooks
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/hooks.mdx
- Reglas de arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Consulta el MDX de esta página antes de realizar modificaciones relevantes; si no puedes acceder, indícalo y no inventes reglas.
2. Revisa los archivos y directorios afectados, incluso cambios de carpetas.
3. **En cualquier carpeta hooks/, cada TS lleva *.hook.ts, declara un useNombre y solo imports y funciones a nivel superior; no type/interface/class/objetos/estado al nivel superior. Preserva tipado y estado.**
4. Conserva el comportamiento y los imports; utiliza TypeScript seguro sin reemplazar tipos con `any`.
5. Comprueba `npm run lint`, `npm run build` y las pruebas existentes cuando estén disponibles.

## Decisiones pendientes

El alcance de estado compartido se define en stores; la ubicación de contratos de tipos reutilizables sigue pendiente. No elimines cachés o sesiones. El Hook reporta cambios pero no corrige archivos por sí solo.

6. Consume el estado compartido desde `src/stores/` o `src/pages/<sección>/stores/` mediante hooks React; no declares caches o clientes al nivel superior de `.hook.ts`. Consulta `react-stores`.
