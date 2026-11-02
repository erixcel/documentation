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
        (src / "index.css").write_text("body { margin: 0; }", encoding="utf-8")
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
        self.assertEqual(len(list((root / "skills").glob("*/SKILL.md"))), 10)
        self.assertEqual(len(hooks["UserPromptSubmit"][0]["hooks"]), 1)
        self.assertEqual(len(hooks["Stop"][0]["hooks"]), 8)

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
        self.write("src/components/card.component.tsx", "export function Card(){ fetch('/api'); return <div/>; }")
        out = self.check_stop("components")
        self.assertIn("src/api", out.get("reason", ""))

    def test_hook_filename_convention(self):
        self.prepare()
        self.write("src/hooks/width.ts", "export function width(){ return 10; }")
        out = self.check_stop("hooks")
        self.assertIn("useXxx", out.get("reason", ""))

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
        self.write("src/api/http.api.ts", "export const url = process.env.API_URL;")
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

    def test_unmodified_files_are_not_blocked(self):
        self.prepare()
        self.assertEqual(self.check_stop("structure"), {})
        self.assertEqual(self.check_stop("config"), {})


if __name__ == "__main__":
    unittest.main()
