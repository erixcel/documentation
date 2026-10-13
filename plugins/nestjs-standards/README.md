# Erixcel NestJS

Plugin de Codex Desktop que agrupa **8 Skills** y **3 Hooks de validación** en una sola instalación.

## Contenido

```text
plugins/nestjs-standards/
├── .codex-plugin/plugin.json
├── skills/
│   ├── nestjs-core/
│   ├── nestjs-db/
│   ├── nestjs-functions/
│   ├── nestjs-global-dto/
│   ├── nestjs-module-dto/
│   ├── nestjs-modules/
│   ├── nestjs-scripts/
│   └── nestjs-tsconfig/
├── hooks/
│   ├── hooks.json
│   ├── detect-changes.py
│   ├── validate-query.py
│   ├── validate-core.py
│   ├── core_validator.py
│   └── validator_common.py
└── tests/test_hooks.py
```

Las Skills consultan las páginas de [documentación de Erixcel](https://docs.erixcel.com/desarrollo/nestjs/creacion-proyecto) como fuente de verdad.

## Hooks

- **UserPromptSubmit — Detect Changes:** registra el estado inicial de archivos `.query.ts` y `.core.ts`.
- **Stop — Query Validator:** comprueba los archivos `.query.ts` modificados. Los archivos Query solo admiten imports, decoradores y **una única clase**: no se permiten constantes ni funciones fuera de ella. Las consultas normales usan una tabla y no hacen JOIN; `-join.query.ts` permite varias tablas y es de solo lectura.
- **Stop — Core Validator:** comprueba los archivos `.core.ts` modificados, sus funciones `setup...` y su integración en `main.ts`.

El plugin no modifica código por sí solo. El validador es **estático y heurístico**: no ejecuta el backend, PostgreSQL, TypeScript ni pruebas de integración. Los logs se guardan en `~/.codex/erixcel-query-validator/query-validator.log` para conservar compatibilidad.

## Instalación / actualización

En **Codex Desktop → Settings → Plugins**, actualiza el marketplace `erixcel/documentation` y después **actualiza o reinstala Erixcel NestJS**. Abre **Settings → Hooks** para revisar, confiar y activar individualmente los tres comandos.

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
