import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
import validator_common as validator


class ReactPluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.frontend = self.base / "frontend"
        self.frontend.mkdir()
        src = self.frontend / "src"
        src.mkdir()
        for name in validator.FOLDERS:
            (src / name).mkdir()
        (src / "main.tsx").write_text(
            "import './index.css';\n"
            "import { createRoot } from 'react-dom/client';\n"
            "import { RouterProvider } from 'react-router-dom';\n"
            "createRoot(document.getElementById('root')!).render(<RouterProvider router={router}/>);\n",
            encoding="utf-8",
        )
        (src / "index.css").write_text("@import 'tailwindcss';\n", encoding="utf-8")
        (src / "routes/path.route.tsx").write_text(
            "import { createBrowserRouter } from 'react-router-dom';\n"
            "export const router = createBrowserRouter([]);\n",
            encoding="utf-8",
        )
        self.package = {
            "name": "frontend", "type": "module",
            "scripts": {k: k for k in ("dev", "build", "lint", "preview", "test")},
            "dependencies": {k: "*" for k in (
                "react", "react-dom", "react-router-dom", "tailwindcss",
                "lucide-react", "@tailwindcss/vite")},
            "devDependencies": {k: "*" for k in ("vite", "typescript", "eslint", "@vitejs/plugin-react")}
        }
        self.write("package.json", json.dumps(self.package))
        self.write(".env.example", "VITE_API_URL=http://localhost:3000\n")
        self.payload = {
            "cwd": str(self.base), "session_id": "test-turn",
            "hook_event_name": "UserPromptSubmit",
        }
        state = self.base / "state"
        state.mkdir()
        self.patch = patch.object(validator, "STATE", state)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def write(self, name, data):
        p = self.frontend / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding="utf-8")

    def prepare(self):
        p = validator.project_for(self.payload)
        self.assertEqual(p, self.frontend)
        validator.store(self.payload, p)

    def check_stop(self, kind):
        return validator.stop({**self.payload, "hook_event_name": "Stop"}, kind)

    def test_installed_config_and_skills(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / ".codex-plugin/plugin.json").read_text())
        hooks = json.loads((root / "hooks/hooks.json").read_text())["hooks"]
        self.assertEqual(manifest["interface"]["displayName"], "Erixcel React")
        self.assertEqual(manifest["version"], "0.2.1")
        self.assertEqual(len(list((root / "skills").glob("*/SKILL.md"))), 11)
        self.assertEqual(len(hooks["UserPromptSubmit"][0]["hooks"]), 1)
        self.assertEqual(len(hooks["Stop"][0]["hooks"]), 7)
        retired = ("validate-structure.py", "validate-module-routes.py", "validate-package.py")
        commands = [h["command"] for h in hooks["Stop"][0]["hooks"]]
        for name in retired:
            self.assertFalse(any(name in command for command in commands), name)

    def test_only_responds_to_react_projects(self):
        backend = self.base / "backend"
        backend.mkdir()
        (backend / "package.json").write_text('{"dependencies":{"@nestjs/core":"*"}}')
        self.assertEqual(validator.stop({**self.payload, "cwd": str(backend), "hook_event_name": "Stop"}, "main"), {})

    def test_snapshot_and_valid_main(self):
        self.prepare()
        self.write("src/main.tsx", (self.frontend / "src/main.tsx").read_text() + "\n// changed")
        self.assertEqual(self.check_stop("main"), {})

    def test_stop_requests_autocorrection_for_main(self):
        self.prepare()
        self.write("src/main.tsx", "createRoot(document.getElementById('root')!).render(null);")
        result = self.check_stop("main")
        self.assertEqual(result["decision"], "block")
        self.assertIn("RouterProvider", result["reason"])
        self.assertIn("index.css", result["reason"])
        repeat = validator.stop({**self.payload, "hook_event_name": "Stop", "stop_hook_active": True}, "main")
        self.assertIn("systemMessage", repeat)
        self.assertNotIn("decision", repeat)

    def test_detects_deleted_directory(self):
        self.prepare()
        (self.frontend / "src/assets").rmdir()
        out = self.check_stop("structure")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("src/assets/", out["reason"])

    def test_components_http_layer(self):
        self.prepare()
        self.write("src/components/simple/card.component.tsx", "export function Card(){ fetch('/api'); return <div/>; }")
        out = self.check_stop("components")
        self.assertIn("delega HTTP", out.get("reason", ""))

    def test_hook_filename_convention(self):
        self.prepare()
        self.write("src/hooks/width.ts", "export function width(){ return 10; }")
        out = self.check_stop("hooks")
        self.assertIn(".hook.ts", out.get("reason", ""))

    def test_route_definition(self):
        self.prepare()
        self.write("src/routes/path.route.tsx", "export const router = [];")
        out = self.check_stop("routes")
        self.assertEqual(out.get("decision"), "block")

    def test_modules_group_by_domain(self):
        self.prepare()
        self.write("src/modules/home.tsx", "export function Home(){return null;}")
        out = self.check_stop("modules")
        self.assertIn("home.tsx", out.get("reason", ""))

    def test_services_use_vite_env(self):
        self.prepare()
        self.write("src/services/fetch.service.ts", "export const fetchData = () => process.env.API_URL;")
        out = self.check_stop("api-services")
        self.assertIn("import.meta.env", out.get("reason", ""))

    def test_environment_names_no_secret_values_in_feedback(self):
        self.prepare()
        self.write(".env", "VITE_API_URL=http://localhost:3000\nVITE_PRIVATE_KEY=NEVER_PRINT_ME\n")
        out = self.check_stop("config")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("VITE_PRIVATE_KEY", out["reason"])
        self.assertNotIn("NEVER_PRINT_ME", out["reason"])

    def test_package_scripts_and_deps(self):
        self.prepare()
        altered = dict(self.package)
        altered["scripts"] = {"dev": "vite"}
        self.write("package.json", json.dumps(altered))
        out = self.check_stop("config")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("script build", out["reason"])

    def test_css_theme_only_allowed(self):
        self.prepare()
        self.write("src/index.css", "@import 'tailwindcss';\n@theme { --color-primary: #2563eb; }\n")
        self.assertEqual(self.check_stop("styles"), {})

    def test_css_rejects_selectors_and_extra_files(self):
        self.prepare()
        self.write("src/index.css", "@import 'tailwindcss';\n.button { color: red; }\n")
        self.write("src/components/simple/button.module.css", ".button { color: blue; }")
        out = self.check_stop("styles")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("index.css", out["reason"])
        self.assertIn("button.module.css", out["reason"])

    def test_api_only_generated_file(self):
        self.prepare()
        self.write("src/api/http.api.ts", "export const api = 1;")
        out = self.check_stop("api")
        self.assertIn("http.api.ts", out.get("reason", ""))
        self.assertIn("backend.api.ts", out.get("reason", ""))

    def test_generated_api_class_and_types_permitted(self):
        self.prepare()
        self.write("src/api/backend.api.ts", "export interface Foo { id: string }\nexport class Api {}\n")
        self.assertEqual(self.check_stop("api"), {})

    def test_components_require_simple_complex_subfolders(self):
        self.prepare()
        self.write("src/components/simple/button.component.tsx", "export function Button(){return <button/>;}")
        result = self.check_stop("components")
        self.assertIn("complex", result.get("reason", ""))

    def test_complex_component_requires_view_and_subfolders(self):
        self.prepare()
        self.write("src/components/complex/audio-recorder/test.ts", "export const x = 1;")
        out = self.check_stop("components")
        self.assertIn("audio-recorder.component.tsx", out.get("reason", ""))
        self.assertIn("hooks/", out.get("reason", ""))
        self.assertIn("services/", out.get("reason", ""))

    def test_hook_ast_allows_inline_types_and_multiple_functions(self):
        self.prepare()
        self.write("src/hooks/use-user.hook.ts",
                   "import { useMemo } from 'react';\n"
                   "export function useUser<T>(user: T | null) { return useMemo(() => !!user, [user]); }\n"
                   "export const helper = (a: string) => a.trim();\n")
        self.assertEqual(self.check_stop("hooks"), {})

    def test_hook_ast_rejects_type_interface_class_and_shared_cache(self):
        self.prepare()
        self.write("src/modules/auth/hooks/use-user.hook.ts",
                   "export type U = { id: number };\n"
                   "interface I { name: string }\n"
                   "class Store {}\n"
                   "const cache = new Map();\n"
                   "export function useUser() { return true; }\n")
        out = self.check_stop("hooks")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("use-user.hook.ts:", out["reason"])
        self.assertIn("Solo imports y funciones", out["reason"])

    def test_hook_ast_does_not_confuse_comments_or_strings(self):
        self.prepare()
        self.write("src/hooks/use-token.hook.ts",
                   "// type Secret = string; class Fake {}\n"
                   "export function useToken() { const str = 'interface Fake {}'; return str; }\n")
        self.assertEqual(self.check_stop("hooks"), {})

    def test_services_ast_rejects_classes_and_types(self):
        self.prepare()
        self.write("src/services/session.service.ts",
                   "export class SessionService {}\n"
                   "export interface Session { id: string }\n"
                   "export const load = () => true;\n")
        out = self.check_stop("services")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("session.service.ts:1", out["reason"])

    def test_nested_service_wrong_extension(self):
        self.prepare()
        self.write("src/components/complex/toast/services/toast.ts", "export function show() {}")
        out = self.check_stop("services")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn(".service.ts", out["reason"])

    def test_service_ast_allows_function_expressions_and_local_variables(self):
        self.prepare()
        self.write("src/modules/auth/services/auth.service.ts",
                   "import type { RequestInit } from 'node-fetch';\n"
                   "export const getUser = async <T>(key: string): Promise<T> => { "
                   "const data = { key }; return data as T; };\n")
        self.assertEqual(self.check_stop("services"), {})

    def test_services_reject_react_hooks(self):
        self.prepare()
        self.write("src/services/session.service.ts",
                   "import { useState } from 'react';\n"
                   "export function getState(){ return useState(0); }\n")
        out = self.check_stop("services")
        self.assertIn("React", out.get("reason", ""))

    def test_module_route_page_placement(self):
        self.prepare()
        self.write("src/routes/not-found.page.tsx", "export const NotFound = () => null;")
        out = self.check_stop("module-routes")
        self.assertIn("not-found.page.tsx", out.get("reason", ""))

    def test_missing_typescript_reports_explicit_error(self):
        self.prepare()
        self.write("src/hooks/use-any.hook.ts", "export function useAny(){return true;}")
        with patch.object(validator.subprocess, "run", side_effect=FileNotFoundError()):
            out = self.check_stop("hooks")
        self.assertIn("TypeScript", out.get("reason", ""))

    def test_unmodified_files_are_not_blocked(self):
        self.prepare()
        self.assertEqual(self.check_stop("main"), {})
        self.assertEqual(self.check_stop("env"), {})


if __name__ == "__main__":
    unittest.main()
