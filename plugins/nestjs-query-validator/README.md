# Erixcel NestJS Validator

Plugin de Codex Desktop con **dos Hooks de ciclo de vida**: `UserPromptSubmit` registra las huellas SHA-256 y `Stop` valida los archivos creados o modificados durante el turno. Sin dependencias adicionales ni escrituras al código.

## Validación de Query

Fuente: https://docs.erixcel.com/desarrollo/nestjs/src/queries-guia

- `nombre.query.ts`: exactamente un import de tabla `*.table` y sin JOIN.
- `nombre-join.query.ts`: puede importar múltiples tablas, pero solo permite SELECT (sin `.insert()`, `.update()` ni `.delete()`).

## Validación de Core

Fuente: https://docs.erixcel.com/desarrollo/nestjs/src/core/index

- Nombre `kebab-case.core.ts`.
- Exactamente una función declarada y exportada: `setupNombre(app: INestApplication)`.
- No inicializar `NestFactory`, iniciar `app.listen()` ni declarar rutas HTTP aquí.
- `src/main.ts` debe importar e invocar la función después de `NestFactory.create` y antes de `app.listen()`.
- Para `traceflow.core.ts` el nombre esperado es `setupTraceFlow`.

## Instalación

Actualiza el marketplace `erixcel/documentation`, instala **Erixcel NestJS Validator** y autoriza ambos Hooks en **Codex Desktop → Settings → Hooks**.

## Comprobación manual

Desde la raíz del plugin ejecuta:

```bash
python3 hooks/query_validator.py --check /ruta/a/src/queries/administrators/administrators.query.ts /ruta/a/src/core/cors.core.ts
```

Log local: `~/.codex/erixcel-query-validator/query-validator.log`.

**Límites:** validación estática con patrones. No ejecuta TypeScript, no verifica tipado, no hace queries a PostgreSQL y no sustituye tests. Solo examina archivos de `src/queries` y `src/core` creados o editados durante el turno. Si falta el snapshot inicial, devuelve un aviso.
