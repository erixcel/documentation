# Erixcel Query Validator

Plugin independiente para Codex Desktop. Contiene **dos hooks**, sin Skill duplicada:

- `UserPromptSubmit`: calcula un snapshot SHA-256 de `src/queries/**/*.query.ts` dentro del workspace.
- `Stop`: compara el snapshot con los archivos actuales y valida **solo archivos creados o modificados durante ese turno**.

Reglas documentadas: https://docs.erixcel.com/desarrollo/nestjs/src/queries-guia

- `nombre.query.ts`: exactamente un import desde `*.table`; JOINs prohibidos.
- `nombre-join.query.ts`: imports de múltiples tablas permitidos; no `.insert()`, `.update()` ni `.delete()`.

Si falla, `Stop` devuelve `{"decision":"block","reason":"..."}` para solicitar una corrección (máximo una continuación automática por turno).

## Prueba manual

```bash
python3 hooks/query_validator.py --check backend/src/queries/administrators/administrators.query.ts backend/src/queries/administrators/administrators-join.query.ts
```

Log local: `~/.codex/erixcel-query-validator/query-validator.log`. No se escribe ni modifica código de tu proyecto ni se accede a la BD.

La comprobación es estática y basada en patrones; **no sustituye** `tsc --noEmit`, ESLint, tests ni ejecución real del backend. Al comenzar un nuevo chat instala/habilita el plugin y autoriza ambos hooks en **Settings → Hooks**. Si no se dispara `UserPromptSubmit`, no se valida el turno y se muestra un aviso.
