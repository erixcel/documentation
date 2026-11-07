import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
import ast

import common.snapshot as snapshot_module
import analyzers.ast as ast_module
from common.constants import FOLDERS
from common.discovery import project_for
from common.snapshot import store
from common.runner import stop
from analyzers.imports import validate_resource_scopes
from validators.pages import validate_page_files
from validators.layouts import validate_layout_files
from validators.functions import validate_functions
from validators.interfaces import validate_interfaces


class ReactPluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.frontend = self.base / "frontend"
        self.frontend.mkdir()
        src = self.frontend / "src"
        src.mkdir()
        for name in FOLDERS:
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
        self.patch = patch.object(snapshot_module, "STATE", state)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def write(self, name, data):
        p = self.frontend / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding="utf-8")

    def prepare(self):
        p = project_for(self.payload)
        self.assertEqual(p, self.frontend)
        store(self.payload, p)

    def check_stop(self, kind):
        return stop({**self.payload, "hook_event_name": "Stop"}, kind)

    def test_root_scripts_exactly_match_registered_hooks(self):
        hooks_dir = Path(__file__).resolve().parents[1] / "hooks"
        config = json.loads((hooks_dir / "hooks.json").read_text(encoding="utf-8"))
        script_names = []
        for groups in config["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    command = hook["command"]
                    self.assertIn("/hooks/", command)
                    filename = command.rsplit("/hooks/", 1)[-1].split('"', 1)[0]
                    self.assertTrue(filename.endswith(".py"), command)
                    script_names.append(filename)
        self.assertEqual(len(script_names), 13)
        self.assertEqual(len(set(script_names)), 13)
        actual = {path.name for path in hooks_dir.glob("*.py")}
        self.assertEqual(actual, set(script_names))
        self.assertEqual(
            {p.name for p in hooks_dir.iterdir() if p.is_file()},
            actual | {"hooks.json"},
        )
        for filename in sorted(actual):
            with self.subTest(filename=filename):
                source = (hooks_dir / filename).read_text(encoding="utf-8")
                root = ast.parse(source)
                for node in ast.walk(root):
                    if isinstance(node, ast.ImportFrom):
                        self.assertNotEqual(node.module, "validator_common")
                    if isinstance(node, ast.Import):
                        self.assertTrue(all(n.name != "validator_common" for n in node.names))

    def test_installed_config_and_skills(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / ".codex-plugin/plugin.json").read_text())
        hooks = json.loads((root / "hooks/hooks.json").read_text())["hooks"]
        self.assertEqual(manifest["interface"]["displayName"], "Erixcel React")
        self.assertEqual(manifest["version"], "0.4.0")
        self.assertEqual(len(list((root / "skills").glob("*/SKILL.md"))), 15)
        self.assertEqual(len(hooks["UserPromptSubmit"][0]["hooks"]), 1)
        self.assertEqual(len(hooks["Stop"][0]["hooks"]), 12)
        retired = ("validate-structure.py", "validate-module-routes.py", "validate-package.py")
        commands = [h["command"] for h in hooks["Stop"][0]["hooks"]]
        for name in retired:
            self.assertFalse(any(name in command for command in commands), name)

    def test_only_responds_to_react_projects(self):
        backend = self.base / "backend"
        backend.mkdir()
        (backend / "package.json").write_text('{"dependencies":{"@nestjs/core":"*"}}')
        self.assertEqual(stop({**self.payload, "cwd": str(backend), "hook_event_name": "Stop"}, "main"), {})

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
        repeat = stop({**self.payload, "hook_event_name": "Stop", "stop_hook_active": True}, "main")
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

    def test_pages_are_grouped_by_feature(self):
        self.prepare()
        self.write("src/pages/home.tsx", "export function Home(){return null;}")
        out = self.check_stop("pages")
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
        self.write("src/pages/auth/hooks/use-user.hook.ts",
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
        self.write("src/pages/auth/services/auth.service.ts",
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
        out = self.check_stop("page-routes")
        self.assertIn("not-found.page.tsx", out.get("reason", ""))

    def test_missing_typescript_reports_explicit_error(self):
        self.prepare()
        self.write("src/hooks/use-any.hook.ts", "export function useAny(){return true;}")
        with patch.object(ast_module.subprocess, "run", side_effect=FileNotFoundError()):
            out = self.check_stop("hooks")
        self.assertIn("TypeScript", out.get("reason", ""))


    def test_resource_scope_cross_subpages_requires_ancestor(self):
        self.write("src/pages/admin/pages/users/functions/format-date.function.ts",
                   "export function formatDate() { return ''; }")
        self.write("src/pages/admin/pages/bettors/bettors.page.tsx",
                   "import { formatDate } from '../users/functions/format-date.function';")
        result = validate_resource_scopes(
            self.frontend, {"src/pages/admin/pages/bettors/bettors.page.tsx"})
        self.assertTrue(any("[resource-scope]" in issue for issue in result))

    def test_resource_scope_parent_import_is_allowed(self):
        self.write("src/pages/admin/functions/format-date.function.ts",
                   "export function formatDate() { return ''; }")
        self.write("src/pages/admin/pages/users/users.page.tsx",
                   "import { formatDate } from '../../functions/format-date.function';")
        self.assertEqual(validate_resource_scopes(
            self.frontend, {"src/pages/admin/pages/users/users.page.tsx"}), [])

    def test_resource_suffix_and_component_nesting(self):
        self.write("src/pages/admin/functions/date.ts", "export function date() { return ''; }")
        self.write("src/pages/admin/components/simple/action.tsx", "export function Action() { return null; }")
        result = validate_resource_scopes(
            self.frontend, {"src/pages/admin/functions/date.ts",
                            "src/pages/admin/components/simple/action.tsx"})
        self.assertEqual(sum("[resource-suffix]" in issue for issue in result), 2)

    def test_pages_have_named_view(self):
        self.write("src/pages/admin/admin.page.tsx", "export function Admin(){return null;}")
        self.write("src/pages/admin/pages/users/users.page.tsx", "export function Users(){return null;}")
        self.assertEqual(validate_page_files(self.frontend, {"src/pages/admin/admin.page.tsx", "src/pages/admin/pages/users/users.page.tsx"}), [])
        self.write("src/pages/auth/auth.tsx", "export function Auth(){return null;}")
        result = validate_page_files(self.frontend, {"src/pages/auth/auth.tsx"})
        self.assertTrue(any("[page-required]" in x for x in result))

    def test_layout_sections_and_forbidden_nested_pages(self):
        self.write("src/pages/admin/layout/topbar/topbar.layout.tsx", "export function Topbar(){return null;}")
        good = validate_layout_files(self.frontend, {"src/pages/admin/layout/topbar/topbar.layout.tsx"})
        self.assertEqual(good, [])
        self.write("src/pages/admin/layout/bottombar/bottombar.tsx", "export function Bottom(){return null;}")
        self.write("src/pages/admin/layout/topbar/pages/inside/inside.page.tsx", "export function Inside(){return null;}")
        bad = validate_layout_files(self.frontend, {"src/pages/admin/layout/bottombar/bottombar.tsx"})
        self.assertTrue(any("[layout-pages]" in x for x in bad))
        self.assertTrue(any("[layout-name]" in x for x in bad))

    def test_function_and_interface_suffixes(self):
        self.write("src/pages/admin/functions/date.ts", "export const date = () => ''")
        self.write("src/pages/admin/interface/user.ts", "export interface User {}")
        self.assertTrue(any(".function.ts" in x for x in validate_functions(self.frontend, {"src/pages/admin/functions/date.ts"})))
        self.assertTrue(any(".interface.ts" in x for x in validate_interfaces(self.frontend, {"src/pages/admin/interface/user.ts"})))

    def test_store_plugin_registered_and_nestjs_isolated(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "hooks/hooks.json").read_text())["hooks"]
        active = [h["command"] for h in config["Stop"][0]["hooks"]]
        self.assertEqual(sum("validate-stores.py" in command for command in active), 1)
        self.assertNotIn("validate-module-routes.py", " ".join(active))
        self.assertTrue((root / "skills/react-stores/SKILL.md").is_file())

    def test_global_store_keeps_top_level_singleton_and_local_type(self):
        self.prepare()
        self.write("src/stores/api-client.store.ts",
                   "type ApiOptions = { path: string };\n"
                   "const api = { url: '/api', request: () => true };\n"
                   "let session = { token: 'test' };\n"
                   "export function getApi() { return api; }\n"
                   "export function getSession() { return session; }\n")
        self.assertEqual(self.check_stop("stores"), {})

    def test_private_store_in_pages_and_deeply_nested_sections(self):
        self.prepare()
        self.write("src/pages/admin/stores/admin-client.store.ts",
                   "const adminApi = { name: 'admin' };\n"
                   "export const getAdminApi = () => adminApi;\n")
        self.write("src/pages/admin/reports/stores/reports.store.ts",
                   "let cache = new Map<string, unknown>();\n"
                   "export function getCache() { return cache; }\n")
        self.assertEqual(self.check_stop("stores"), {})

    def test_store_does_not_require_creating_empty_folders(self):
        self.prepare()
        self.write("src/pages/admin/admin.tsx", "export function Admin() { return null; }\n")
        self.assertEqual(self.check_stop("stores"), {})

    def test_store_rejects_non_store_filename_in_touched_store_folder(self):
        self.prepare()
        self.write("src/stores/auth-session.store.ts", "let state = null;\nexport function getState() { return state; }\n")
        self.write("src/stores/legacy.ts", "export const cache = new Map();\n")
        out = self.check_stop("stores")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("src/stores/legacy.ts:1", out["reason"])
        self.assertIn("[store-name]", out["reason"])

    def test_store_rejects_file_outside_global_or_page_store_locations(self):
        self.prepare()
        self.write("src/pages/admin/admin-client.store.ts", "export const client = {};\n")
        self.write("src/components/simple/cache.store.ts", "export const cache = {};\n")
        out = self.check_stop("stores")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("admin-client.store.ts:1", out["reason"])
        self.assertIn("cache.store.ts:1", out["reason"])
        self.assertIn("[store-location]", out["reason"])

    def test_store_rejects_nested_store_subfolders_and_wrong_suffix(self):
        self.prepare()
        self.write("src/pages/admin/stores/deep/legacy.store.ts", "export let cache = {};\n")
        self.write("src/pages/admin/stores/bad.store.tsx", "export const state = 5;\n")
        out = self.check_stop("stores")
        self.assertIn("legacy.store.ts:1", out.get("reason", ""))
        self.assertIn("bad.store.tsx:1", out.get("reason", ""))

    def test_store_rejects_react_hooks_and_jsx_ast(self):
        self.prepare()
        self.write("src/stores/bad.store.tsx",
                   "import { useState as state } from 'react';\n"
                   "const a = state(0);\n"
                   "export function View(){ return <main/>; }\n")
        out = self.check_stop("stores")
        self.assertIn("[store-react-hook]", out.get("reason", ""))
        self.assertIn("[store-jsx]", out.get("reason", ""))

    def test_store_rejects_reactdom_import_and_mount(self):
        self.prepare()
        self.write("src/stores/dom.store.ts",
                   "import { createRoot } from 'react-dom/client';\n"
                   "export const app = createRoot(document.getElementById('root')!);\n")
        out = self.check_stop("stores")
        self.assertIn("[store-reactdom]", out.get("reason", ""))
        self.assertIn("[store-react-render]", out.get("reason", ""))

    def test_store_rejects_type_only_container(self):
        self.prepare()
        self.write("src/stores/contracts.store.ts", "export type Token = string;\nexport interface Data { id: string }\n")
        out = self.check_stop("stores")
        self.assertIn("[store-empty]", out.get("reason", ""))

    def test_store_does_not_mistake_strings_comments_or_types_for_hooks(self):
        self.prepare()
        self.write("src/pages/bettor/stores/auth.store.ts",
                   "// useState() is only a comment.\n"
                   "type Auth = { message: string };\n"
                   "let session: Auth | null = { message: 'React.useEffect() JSX <div/>' };\n"
                   "export function getSession() { return session; }\n")
        self.assertEqual(self.check_stop("stores"), {})

    def test_store_modified_directory_validates_unchanged_sibling(self):
        self.write("src/stores/old.ts", "export const value = 1;\n")
        self.prepare()
        self.write("src/stores/new.store.ts", "export const cache = {};\n")
        out = self.check_stop("stores")
        self.assertIn("src/stores/old.ts:1", out.get("reason", ""))

    def test_store_move_and_delete_are_handled_by_snapshot(self):
        self.write("src/pages/admin/stores/original.store.ts", "export const state = { id: 1 };\n")
        self.prepare()
        original = self.frontend / "src/pages/admin/stores/original.store.ts"
        original.unlink()
        self.write("src/stores/moved.store.ts", "export const state = { id: 1 };\n")
        self.assertEqual(self.check_stop("stores"), {})

    def test_existing_service_and_hook_function_only_rules_remain(self):
        self.prepare()
        self.write("src/pages/admin/services/admin.service.ts",
                   "const api = new Map();\nexport function getApi() { return api; }\n")
        self.write("src/pages/admin/hooks/use-auth.hook.ts",
                   "const session = { token: '' };\nexport function useAuth() { return session; }\n")
        self.assertIn("Solo funciones", self.check_stop("services").get("reason", ""))
        self.assertIn("Solo funciones", self.check_stop("hooks").get("reason", ""))

    def test_store_validator_does_not_run_in_nestjs_backend(self):
        self.prepare()
        backend = self.base / "backend"
        backend.mkdir()
        (backend / "package.json").write_text('{"dependencies":{"@nestjs/core":"*"}}')
        self.assertEqual(stop({**self.payload, "cwd": str(backend),
                                        "hook_event_name": "Stop"}, "stores"), {})

    def test_unmodified_files_are_not_blocked(self):
        self.prepare()
        self.assertEqual(self.check_stop("main"), {})
        self.assertEqual(self.check_stop("env"), {})


if __name__ == "__main__":
    unittest.main()
