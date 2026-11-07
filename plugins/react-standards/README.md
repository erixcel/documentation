# Erixcel React

Plugin independiente de Erixcel NestJS (v0.4.0). **15 Skills y 13 Hooks** para React 19, TypeScript, React Router 7, Tailwind CSS 4 y Vite 8.

Fuente de verdad: [documentación React](https://docs.erixcel.com/desarrollo/react/estructura). Las Skills enlazan a las páginas MDX; las recomendaciones de arquitectura se adaptan al proyecto real.

Estructura de referencia: `src/api`, `src/assets`, `src/components`, `src/hooks`, `src/pages`, `src/routes`, `src/services`, `src/stores`, `src/main.tsx`, `src/index.css`. Archivos raíz: `package.json`, `.env`, `.env.example`.

## Hooks activos en v0.4.0

- **UserPromptSubmit:** Detect Changes registra cambios antes de que Codex trabaje.
- **Stop (12):** Main, Style, API, Component, React Hook, Service, Store, Env, Function, Page, Interface y Layout Validator.

**Retirados por flexibilidad entre proyectos:** Structure Validator, Module & Route Validator y Package Validator. Se eliminaron de `hooks.json` y de la distribución del plugin, por lo que no se ejecutan al terminar Codex.

Las convenciones de carpetas de páginas, las recomendaciones para package.json y la estructura principal siguen documentadas como **guías**, no como validaciones automáticas obligatorias. Los validadores existentes no modifican archivos por sí solos.

Para probar manualmente un Hook de los que siguen activos:

```sh
python3 hooks/validate-hooks.py --check /ruta/al/frontend
```

Autoriza/activa los Hooks en **Codex Desktop → Settings → Hooks**. Si el plugin ya estaba instalado, actualízalo a v0.4.0 y comprueba que los tres Hooks retirados hayan desaparecido.

La Skill `react-pages` y la guía `src/pages/` documentan la organización recomendada por página. No se ha registrado ningún Hook obligatorio de estructura global o páginas/rutas en `hooks.json`.

Los stores `*.store.ts` guardan estado y clientes en `src/stores/` o `src/pages/<sección>/stores/`; no se comparte estado entre sesiones administrativas y de apostador. Estas invariantes deben probarse en ejecución.

## Alcance mínimo compartido (obligatorio)

Cada recurso de React (functions, hooks, components, services, interfaces y stores) vive en el **ancestro común más cercano de todos sus consumidores**, nunca en un nivel más alto por comodidad. Antes de crearlo o moverlo, identifica sus imports reales y el ámbito de cada consumidor. Si solo lo usa `src/pages/admin/pages/users`, ubícalo en su carpeta `functions/`, `hooks/`, `components/`, `services/`, `interfaces/` o `stores/`. Si lo comparten `users` y `bettors` dentro de admin, súbelo a `src/pages/admin/<tipo>/`; si lo usan admin y main, a `src/<tipo>/`. Esto también aplica a niveles intermedios más profundos.

Ejemplo: `src/pages/admin/pages/users/functions/format-date.function.ts` → `src/pages/admin/functions/format-date.function.ts` → `src/functions/format-date.function.ts`, según sus consumidores. Los sufijos son `.function.ts`, `.hook.ts`, `.service.ts`, `.interface.ts`, `.store.ts` y `.component.tsx`.

Los componentes usan `components/simple/` o `components/complex/` **en todos los ámbitos** (globales, páginas y subpáginas). Un componente complex conserva carpeta propia, vista `nombre.component.tsx` y subcarpetas de hooks y services cuando las exija la convención actual. Nunca dupliques archivos para compartirlos ni uses `index.ts` para reexportar recursos privados: mueve el archivo al ancestro común más cercano y ajusta los imports directos. Los `index.ts` públicos de página siguen permitidos, pero no como puente para exponer recursos privados.

Las funciones React son **funciones ordinarias de TypeScript**, no clases ni decoradores NestJS; no uses `@Injectable` ni otras convenciones del backend. Las verificaciones estáticas solo pueden probar rutas, nombres y dependencias/imports resolubles; usos dinámicos o referencias indirectas requieren revisión manual.


## Páginas y layouts: regla obligatoria

Cada página principal o subpágina vive dentro de su propia carpeta y tiene **exactamente una vista** con el nombre de la carpeta y sufijo `*.page.tsx`: `src/pages/admin/admin.page.tsx`, `src/pages/auth/auth.page.tsx`, `src/pages/admin/pages/users/users.page.tsx`. Nunca `admin.tsx` ni `auth.tsx` como vistas de página. Las subpáginas se alojan exclusivamente en `pages/` de otra página.

Cada página puede tener **solo las carpetas que realmente necesite**: `components/` (siempre `simple/` y `complex/`), `functions/` (`*.function.ts`), `hooks/` (`*.hook.ts`), `interface/` (`*.interface.ts`; también se admite `interfaces/`), `services/` (`*.service.ts`), `stores/` (`*.store.ts`), `pages/` y `layout/`. No crear carpetas vacías ni obligar todas las carpetas en páginas simples.

`layout/` sirve para **dividir una sola página grande en secciones internas con lógica o representación sustancial**, no para crear rutas o subpáginas. Ejemplo: `src/pages/auth/layout/topbar/topbar.layout.tsx` y `src/pages/auth/layout/bottombar/bottombar.layout.tsx`. Si hay solo una vista sencilla, no hace falta layout. Cada sección tiene su propia carpeta, la vista `<sección>.layout.tsx` y sus propios recursos opcionales (functions, hooks, components, services, interfaces, stores). Queda **prohibido cualquier directorio `pages/` dentro de `layout/` a cualquier profundidad**. Las páginas hijas van en `src/pages/<padre>/pages/<hija>/`.

La regla del ancestro común más cercano también rige los recursos dentro de layouts y páginas. Los validadores `Page`, `Layout`, `Function`, `Interface` están registrados como Hooks Stop adicionales; las comprobaciones no modifican ni migran archivos automáticamente.


## Arquitectura modular de los Hooks

Los ejecutables `validate-*.py` siguen registrados individualmente en `hooks.json`; son wrappers sin reglas embebidas. `common/` contiene `discovery.py`, `snapshot.py`, `runner.py`, `reporter.py` y constantes. `validators/` contiene un módulo por recurso (`pages.py`, `layouts.py`, `functions.py`, `interfaces.py`, `hooks.py`, `components.py`, `services.py`, `stores.py`, etc.). `analyzers/` incluye `imports.py`, `ast.py` y `typescript-ast.mjs` para análisis estático de imports y del AST TypeScript. Se retiró `validator_common.py`, así como las entradas antiguas de la raíz `validate-api-services.py`, `validate-config.py`, `validate-routes.py` y `validate-ast.mjs`. Los **13 scripts Python** de la raíz (1 `UserPromptSubmit` y 12 `Stop`) corresponden exactamente a los **13 Hooks** de `hooks.json`; ese JSON es únicamente configuración, no un Hook adicional. Los imports internos utilizan directamente `common/`, `validators/` y `analyzers/`, y el analizador TypeScript vive en `analyzers/typescript-ast.mjs`.

La separación es interna: se conservan los nombres y contratos de los 13 Hooks. Los validadores no modifican archivos. Para ejecutar las pruebas: `python3 -m unittest discover -s plugins/react-standards/tests -p "test_*.py" -v` (requiere dependencias del parser TypeScript cuando se prueban reglas AST).
