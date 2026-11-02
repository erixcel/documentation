---
name: react-stores
description: "Usar al crear o modificar *.store.ts, sesiones compartidas, clientes persistentes, caches o suscripciones en frontend React + Vite."
---

# react-stores

## Fuente de verdad

- Página: https://docs.erixcel.com/desarrollo/react/src/stores
- MDX: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/react/src/stores.mdx
- Arquitectura: https://docs.erixcel.com/desarrollo/react/estructura

## Procedimiento

1. Identifica consumidores. Varias páginas principales: `src/stores/`. Solo una sección o sus subpáginas: `src/pages/<sección>/stores/`. No globalices por comodidad.
2. Usa `*.store.ts` y conserva las mismas instancias, sesiones, suscripciones, cachés y caducidad. Se permiten constantes e inicialización a nivel superior, a diferencia de hooks y servicios. No crees stores vacíos.
3. Sin JSX, componentes React, ReactDOM ni llamadas a React Hooks. Proporciona accessors (`getApi`, `getAdminApi`, `getAdminSession`) que devuelvan instancias existentes; los servicios las consumen mediante funciones.
4. Separa sesiones administrativas y de apostador. Un 401 administrativo no cierra la sesión del apostador; una respuesta antigua no borra una sesión renovada. Evita dependencias circulares.
5. Usa lint, build, el Store Validator y pruebas de comportamiento. El AST no prueba identidad, alcance real, persistencia ni carreras entre respuestas.

Los contratos de tipos reutilizables mantienen su decisión de ubicación independiente. No fuerces stores vacíos ni elimines tipos o estado existentes.
