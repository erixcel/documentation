"""Regression tests for the three Codex hooks (no third-party dependencies)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
MAIN = """import { setupCors } from '@core/cors.core';
const app = await NestFactory.create(AppModule);
setupCors(app);
await app.listen(3000);
"""
VALID_CORE = """import type { INestApplication } from '@nestjs/common';
export function setupCors(app: INestApplication): void {
  app.enableCors();
}
"""
QUERY = """import { administrators } from '@db/tables/administrators.table';
export class AdministratorsQuery {}
"""


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "repo"
        src = self.root / "backend/src"
        self.core = src / "core/cors.core.ts"
        self.query = src / "queries/administrators/administrators.query.ts"
        self.main = src / "main.ts"
        for file in (self.core, self.query, self.main):
            file.parent.mkdir(parents=True, exist_ok=True)
        self.core.write_text(VALID_CORE)
        self.query.write_text(QUERY)
        self.main.write_text(MAIN)
        self.env = dict(os.environ, HOME=str(base / "home"))
        self.turn = 0

    def invoke(self, name, event, active=False):
        payload = {
            "session_id": "test-session",
            "turn_id": f"turn-{self.turn}",
            "cwd": str(self.root),
            "hook_event_name": event,
            "stop_hook_active": active,
        }
        result = subprocess.run(
            [sys.executable, str(HOOKS / name)],
            input=json.dumps(payload), capture_output=True, text=True,
            env=self.env, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def begin(self):
        self.turn += 1
        self.assertEqual(self.invoke("detect-changes.py", "UserPromptSubmit"), {})

    def test_valid_files_do_not_block(self):
        self.begin()
        self.query.write_text(QUERY + "// harmless comment\n")
        self.core.write_text(VALID_CORE + "// harmless comment\n")
        self.assertEqual(self.invoke("validate-query.py", "Stop"), {})
        self.assertEqual(self.invoke("validate-core.py", "Stop"), {})

    def test_query_and_core_are_independent(self):
        self.begin()
        self.query.write_text(QUERY + "import { users } from '@db/tables/users.table';\n")
        query = self.invoke("validate-query.py", "Stop")
        self.assertEqual(query.get("decision"), "block")
        self.assertIn("una tabla", query.get("reason", ""))
        self.assertEqual(self.invoke("validate-core.py", "Stop"), {})

        self.begin()
        self.query.write_text(QUERY)
        self.core.write_text(VALID_CORE.replace("setupCors(app: INestApplication)", "wrong(app: INestApplication, extra: string)"))
        core = self.invoke("validate-core.py", "Stop")
        self.assertEqual(core.get("decision"), "block")
        self.assertIn("setupCors", core.get("reason", ""))
        self.assertEqual(self.invoke("validate-query.py", "Stop").get("decision"), None)

    def test_join_query_is_read_only(self):
        self.begin()
        joined = self.query.with_name("administrators-join.query.ts")
        joined.write_text("""import { administrators } from '@db/tables/administrators.table';
import { users } from '@db/tables/users.table';
@Injectable()
export class AdministratorsJoinQuery {
  async list() {
    return database.select().from(administrators)
      .innerJoin(users, eq(administrators.userId, users.id));
  }
}
""")
        self.assertEqual(self.invoke("validate-query.py", "Stop"), {})
        joined.write_text(joined.read_text().replace(
            "return database.select()",
            "await database.update(users).set({ active: false });\n    return database.select()"
        ))
        self.assertEqual(self.invoke("validate-query.py", "Stop").get("decision"), "block")

    def test_core_main_integration(self):
        self.begin()
        self.core.write_text(VALID_CORE + "// touched\n")
        self.main.write_text("const app = await NestFactory.create(AppModule);\nawait app.listen(3000);\n")
        out = self.invoke("validate-core.py", "Stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("main.ts", out.get("reason", ""))

    def test_top_level_constants_request_correction(self):
        self.begin()
        self.query.write_text("""import { administrators } from '@db/tables/administrators.table';
const fields = { id: administrators.id };
const visible = () => true;
@Injectable()
export class AdministratorsQuery {
  async list() { return database.select(fields).from(administrators).where(visible()); }
}
""")
        result = self.invoke("validate-query.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("fuera de la clase", result.get("reason", ""))
        self.assertIn("Línea 2", result.get("reason", ""))
        self.assertIn("Línea 3", result.get("reason", ""))
        self.assertIn("this.fields", result.get("reason", ""))
        self.query.write_text("""import { administrators } from '@db/tables/administrators.table';
@Injectable()
export class AdministratorsQuery {
  private readonly fields = { id: administrators.id };
  private readonly visible = () => true;
  async list() {
    const local = 1;
    return database.select(this.fields).from(administrators).where(this.visible());
  }
}
""")
        self.assertEqual(self.invoke("validate-query.py", "Stop"), {})

    def test_only_one_class(self):
        self.begin()
        self.query.write_text(QUERY + "export class AnotherQuery {}\n")
        result = self.invoke("validate-query.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("exactamente una clase", result.get("reason", ""))

    def test_outside_function_or_variable_after_class(self):
        self.begin()
        self.query.write_text(QUERY + "export function helper() { return 1; }\n")
        self.assertEqual(self.invoke("validate-query.py", "Stop").get("decision"), "block")
        self.begin()
        self.query.write_text(QUERY + "const foo = 1;\n")
        self.assertEqual(self.invoke("validate-query.py", "Stop").get("decision"), "block")

    def test_join_query_class_allows_internal_constants(self):
        self.begin()
        joined = self.query.with_name("administrators-join.query.ts")
        joined.write_text("""import { administrators } from '@db/tables/administrators.table';
import { users } from '@db/tables/users.table';
@Injectable()
export class AdministratorsJoinQuery {
  async list() {
    const fields = { id: administrators.id };
    const visible = () => true;
    const brace = /[{}]/;
    return database.select(fields).from(administrators)
      .innerJoin(users, eq(administrators.userId, users.id));
  }
}
""")
        self.assertEqual(self.invoke("validate-query.py", "Stop"), {})

    def test_no_snapshot_only_warns(self):
        out = self.invoke("validate-core.py", "Stop")
        self.assertNotIn("decision", out)
        self.assertIn("snapshot", out.get("systemMessage", ""))


if __name__ == "__main__":
    unittest.main()
