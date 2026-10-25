# Erixcel NestJS

Plugin de Codex Desktop que agrupa **8 Skills** y **12 Hooks de validación** en una sola instalación.

## Contenido

```text
plugins/nestjs-standards/
├── .codex-plugin/plugin.json
├── skills/                       # 8 Skills
├── hooks/
│   ├── hooks.json
│   ├── detect-changes.py          # UserPromptSubmit
│   ├── validate-query.py         # Stop
│   ├── validate-core.py
│   ├── validate-controller.py
│   ├── validate-service.py
│   ├── validate-module.py
│   ├── validate-dto.py
│   ├── validate-function.py
│   ├── validate-table.py
│   ├── validate-seed.py
│   ├── validate-script.py
│   ├── validate-tsconfig.py
│   ├── validator_common.py
│   ├── core_validator.py
│   ├── query_structure.py
│   └── extra_rules.py
└── tests/
    ├── test_hooks.py
    └── test_extended_hooks.py
```

Las Skills consultan las páginas de [documentación de Erixcel](https://docs.erixcel.com/desarrollo/nestjs/creacion-proyecto) como fuente de verdad.

## Hooks

### Antes de comenzar (1)
- **Detect Changes** (`UserPromptSubmit`): registra archivos vigilados de NestJS al iniciar cada turno.

### Al terminar (11)
- **Query Validator** (`*.query.ts`): una sola clase por archivo; separación de consultas normales y con JOIN.
- **Core Validator** (`*.core.ts`): función única `setupNombre(app)` e integración en `main.ts`.
- **Controller Validator** (`*.controller.ts`): clases Controller, decoradores Swagger/TraceNode, delegación directa al Service y un DTO `<metodo-en-kebab-case>.dto.ts` por cada método (excepto `constructor`). Solo esos DTO deben existir en el directorio `dto/`; revisa también cambios en los propios DTO.
- **Service Validator** (`*.service.ts`): clase Injectable y acceso a datos a través de Queries.
- **Module Validator** (`*.module.ts`): clase Module y metadatos; dentro de `src/modules/**` solo el `<nombre>.module.ts` es obligatorio. `<nombre>.controller.ts` y `<nombre>.service.ts` son **opcionales**, pero deben compartir su base y no deben existir otros archivos hermanos. Admite subcarpetas de responsabilidad; todo submódulo debe agruparse recursivamente en `modules/<nombre>/<nombre>.module.ts` dentro del padre, nunca como una carpeta suelta junto a su `.module.ts`. Utiliza `functions/*.function.ts` para utilidades estáticas y submódulos para servicios adicionales con DI. El Hook revisa altas, ediciones y bajas de archivos hermanos. **La única excepción es `src/app.module.ts`**. `src/security/security.module.ts` y los demás módulos dentro de `src` también cumplen la regla; mueve Guards, configuración y servicios adicionales a subcarpetas o submódulos preservando imports y DI.
- **DTO Validator** (`*.dto.ts`): clases Dto, trazabilidad y ausencia de lógica de BD.
- **Function Validator** (`*.function.ts`): una sola clase exportada y exclusivamente imports a nivel superior, sin tipos/interfaces/constantes o funciones sueltas. Cada método, también privado, debe ser `static` y llevar `@TraceNode({ name, type: 'method' })` desde `@erixcel/traceflow`.
- **Table Validator** (`*.table.ts`): Drizzle `pgTable`, tres campos de auditoría y tipos inferidos.
- **Seed Validator** (`src/seeds/**`): carpeta plana con solo `*.seed.ts`, sin subcarpetas, JSON ni archivos auxiliares. Cada seed permite imports y una única función exportada `seedNombre(...)` para una tabla, sin `type`/`interface` ni declaraciones independientes. Los datos y constantes van dentro de la función; no se necesita TraceFlow. Detect Changes también registra creaciones, cambios y eliminaciones de cualquier archivo o carpeta de `src/seeds/`, incluso carpetas vacías.
- **Script Validator** (`scripts/*.ts`): nombres y prevención básica de secretos/rutas absolutas.
- **TSConfig Validator** (`tsconfig.json`): JSONC válido y coherencia básica de `compilerOptions`.

Cada Hook se activa o desactiva de forma independiente en **Codex Desktop → Settings → Hooks**. Los comandos `Stop` leen el mismo snapshot; un incumplimiento devuelve `decision: "block"` e instrucciones para que Codex intente corregirlo automáticamente.

Estas comprobaciones son **heurísticas** y no sustituyen el compilador, ESLint ni las pruebas. Se aplican a los archivos creados o modificados durante el turno. Seed Validator se activa también cuando cambia cualquier archivo o carpeta bajo src/seeds/, para revisar su estructura completa. No se aplican a proyectos ajenos a NestJS ni a carpetas sin cambios.

El plugin no modifica código por sí solo. El validador es **estático y heurístico**: no ejecuta el backend, PostgreSQL, TypeScript ni pruebas de integración. Los logs se guardan en `~/.codex/erixcel-query-validator/query-validator.log` para conservar compatibilidad.

## Instalación / actualización

En **Codex Desktop → Settings → Plugins**, actualiza el marketplace `erixcel/documentation` y después **actualiza o reinstala Erixcel NestJS**. Abre **Settings → Hooks** para revisar, confiar y activar individualmente los doce comandos.

Si instalaste por separado el antiguo **Erixcel NestJS Validators**, desinstálalo para que sus Hooks no se ejecuten dos veces.

## Pruebas manuales

Desde la raíz de este plugin:

```bash
python3 hooks/validate-query.py --check /ruta/a/src/queries/administrators/administrators.query.ts
python3 hooks/validate-core.py --check /ruta/a/src/core/cors.core.ts
```

Pruebas de ciclo de vida:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Documentación: [Skills](https://docs.erixcel.com/ia/skills) · [Hooks](https://docs.erixcel.com/ia/hooks).
