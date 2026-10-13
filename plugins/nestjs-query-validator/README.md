# Erixcel NestJS Validators

Plugin de Codex Desktop: **tres Hooks registrados**, dos validadores independientes.

```text
UserPromptSubmit
└── detect-changes.py

Stop
├── validate-query.py
└── validate-core.py
```

- **Detect Changes** calcula un snapshot SHA-256 de `src/queries/**/*.query.ts` y `src/core/*.core.ts` al enviar el prompt.
- **Query Validator** comprueba solo archivos `.query.ts` creados o modificados durante el turno.
- **Core Validator** comprueba solo archivos `.core.ts` creados o modificados durante el turno.

Los validadores `Stop` leen **el mismo snapshot** y pueden ejecutarse en paralelo. No escriben sobre archivos del proyecto. Sus lógicas están separadas para poder confiar, activar o desactivar cada Hook individualmente.

## Convenciones que se aplican

[Query](https://docs.erixcel.com/desarrollo/nestjs/src/queries-guia):
- `nombre.query.ts`: solo una tabla importada; sin JOIN.
- `nombre-join.query.ts`: múltiples tablas permitidas, sin escrituras.

[Core](https://docs.erixcel.com/desarrollo/nestjs/src/core/index):
- archivo `kebab-case.core.ts`;
- única función exportada `setupNombre(app: INestApplication)`;
- sin inicialización NestFactory ni escucha HTTP;
- importación y llamada desde `src/main.ts` antes de escuchar.
- caso especial: `traceflow.core.ts` → `setupTraceFlow`.

## Instalar y probar

Desde **Codex Desktop → Settings → Plugins**, actualiza tu marketplace `erixcel/documentation` e instala o actualiza **Erixcel NestJS Validators**. En **Settings → Hooks**, revisa y autoriza individualmente los tres comandos.

Para una prueba manual, en la carpeta raíz de este plugin:

```bash
python3 hooks/validate-query.py --check /ruta/src/queries/administrators/administrators.query.ts
python3 hooks/validate-core.py --check /ruta/src/core/cors.core.ts
```

Los eventos deben compartir `session_id`, `turn_id` y `cwd` para detectar cambios en una misma interacción. Sin snapshot, las validaciones avisan y no bloquean.

Log local: `~/.codex/erixcel-query-validator/query-validator.log` (compatibilidad con versión anterior).

**Limitaciones:** son comprobaciones estáticas y heurísticas, no compilación de TypeScript, ESLint ni pruebas de ejecución o base de datos. Por defecto solo se examinan los archivos modificados desde el comienzo del turno.
