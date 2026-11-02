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

## Alcance mínimo compartido (obligatorio)

Cada recurso de React (functions, hooks, components, services, interfaces y stores) vive en el **ancestro común más cercano de todos sus consumidores**, nunca en un nivel más alto por comodidad. Antes de crearlo o moverlo, identifica sus imports reales y el ámbito de cada consumidor. Si solo lo usa `src/pages/admin/pages/users`, ubícalo en su carpeta `functions/`, `hooks/`, `components/`, `services/`, `interfaces/` o `stores/`. Si lo comparten `users` y `bettors` dentro de admin, súbelo a `src/pages/admin/<tipo>/`; si lo usan admin y main, a `src/<tipo>/`. Esto también aplica a niveles intermedios más profundos.

Ejemplo: `src/pages/admin/pages/users/functions/format-date.function.ts` → `src/pages/admin/functions/format-date.function.ts` → `src/functions/format-date.function.ts`, según sus consumidores. Los sufijos son `.function.ts`, `.hook.ts`, `.service.ts`, `.interface.ts`, `.store.ts` y `.component.tsx`.

Los componentes usan `components/simple/` o `components/complex/` **en todos los ámbitos** (globales, páginas y subpáginas). Un componente complex conserva carpeta propia, vista `nombre.component.tsx` y subcarpetas de hooks y services cuando las exija la convención actual. Nunca dupliques archivos para compartirlos ni uses `index.ts` para reexportar recursos privados: mueve el archivo al ancestro común más cercano y ajusta los imports directos. Los `index.ts` públicos de página siguen permitidos, pero no como puente para exponer recursos privados.

Las funciones React son **funciones ordinarias de TypeScript**, no clases ni decoradores NestJS; no uses `@Injectable` ni otras convenciones del backend. Las verificaciones estáticas solo pueden probar rutas, nombres y dependencias/imports resolubles; usos dinámicos o referencias indirectas requieren revisión manual.
