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

## Alcance mínimo compartido (obligatorio)

Cada recurso de React (functions, hooks, components, services, interfaces y stores) vive en el **ancestro común más cercano de todos sus consumidores**, nunca en un nivel más alto por comodidad. Antes de crearlo o moverlo, identifica sus imports reales y el ámbito de cada consumidor. Si solo lo usa `src/pages/admin/pages/users`, ubícalo en su carpeta `functions/`, `hooks/`, `components/`, `services/`, `interfaces/` o `stores/`. Si lo comparten `users` y `bettors` dentro de admin, súbelo a `src/pages/admin/<tipo>/`; si lo usan admin y main, a `src/<tipo>/`. Esto también aplica a niveles intermedios más profundos.

Ejemplo: `src/pages/admin/pages/users/functions/format-date.function.ts` → `src/pages/admin/functions/format-date.function.ts` → `src/functions/format-date.function.ts`, según sus consumidores. Los sufijos son `.function.ts`, `.hook.ts`, `.service.ts`, `.interface.ts`, `.store.ts` y `.component.tsx`.

Los componentes usan `components/simple/` o `components/complex/` **en todos los ámbitos** (globales, páginas y subpáginas). Un componente complex conserva carpeta propia, vista `nombre.component.tsx` y subcarpetas de hooks y services cuando las exija la convención actual. Nunca dupliques archivos para compartirlos ni uses `index.ts` para reexportar recursos privados: mueve el archivo al ancestro común más cercano y ajusta los imports directos. Los `index.ts` públicos de página siguen permitidos, pero no como puente para exponer recursos privados.

Las funciones React son **funciones ordinarias de TypeScript**, no clases ni decoradores NestJS; no uses `@Injectable` ni otras convenciones del backend. Las verificaciones estáticas solo pueden probar rutas, nombres y dependencias/imports resolubles; usos dinámicos o referencias indirectas requieren revisión manual.
