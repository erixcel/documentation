# Erixcel React

Plugin independiente de Erixcel NestJS (v0.2.2). **11 Skills y 8 Hooks** para React 19, TypeScript, React Router 7, Tailwind CSS 4 y Vite 8.

Fuente de verdad: [documentación React](https://docs.erixcel.com/desarrollo/react/estructura). Las Skills enlazan a las páginas MDX; las recomendaciones de arquitectura se adaptan al proyecto real.

Estructura de referencia: `src/api`, `src/assets`, `src/components`, `src/hooks`, `src/pages`, `src/routes`, `src/services`, `src/main.tsx`, `src/index.css`. Archivos raíz: `package.json`, `.env`, `.env.example`.

## Hooks activos en v0.2.1

- **UserPromptSubmit:** Detect Changes registra cambios antes de que Codex trabaje.
- **Stop (7):** Main, Style, API, Component, React Hook, Service y Env Validator.

**Retirados por flexibilidad entre proyectos:** Structure Validator, Module & Route Validator y Package Validator. Se eliminaron de `hooks.json` y de la distribución del plugin, por lo que no se ejecutan al terminar Codex.

Las convenciones de carpetas de páginas, las recomendaciones para package.json y la estructura principal siguen documentadas como **guías**, no como validaciones automáticas obligatorias. Los validadores existentes no modifican archivos por sí solos.

Para probar manualmente un Hook de los que siguen activos:

```sh
python3 hooks/validate-hooks.py --check /ruta/al/frontend
```

Autoriza/activa los Hooks en **Codex Desktop → Settings → Hooks**. Si el plugin ya estaba instalado, actualízalo a v0.2.1 y comprueba que los tres Hooks retirados hayan desaparecido.

La Skill `react-pages` y la guía `src/pages/` documentan la organización recomendada por página. No se ha registrado ningún Hook obligatorio de estructura global o páginas/rutas en `hooks.json`.
