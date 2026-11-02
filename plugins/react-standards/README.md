# Erixcel React

Plugin independiente de Erixcel NestJS. 10 Skills y 9 Hooks sobre React 19, TypeScript, React Router 7, Tailwind 4 y Vite 8.

Fuente de verdad: [documentación React](https://docs.erixcel.com/desarrollo/react/estructura). Las Skills enlazan a las páginas MDX de este repositorio; no duplican reglas extensas.

Estructura: `src/api`, `src/assets`, `src/components`, `src/hooks`, `src/modules`, `src/routes`, `src/services`, `src/main.tsx` e `src/index.css`; archivos raíz revisados: `package.json`, `.env` y `.env.example`.

Hooks: un snapshot en UserPromptSubmit y ocho validaciones independientes en Stop. Se aplican solo a carpetas React + Vite reconocidas y nunca modifican archivos. Para probar manualmente: `python3 hooks/validate-react.py --check /ruta/al/frontend`.

Los Hooks deben autorizarse y activarse en Codex Desktop → Settings → Hooks después de instalar el plugin desde el marketplace `erixcel/documentation`.
