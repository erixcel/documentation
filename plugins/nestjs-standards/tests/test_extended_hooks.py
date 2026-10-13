"""Lifecycle checks for Erixcel NestJS extended file-type validators."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"


class OtherValidators(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "repo"
        self.backend = self.root / "backend"
        (self.backend / "src").mkdir(parents=True)
        (self.backend / "src/main.ts").write_text("void 0;\n")
        self.env = dict(os.environ, HOME=str(base / "home"))
        self.turn = 0

    def put(self, relative, code):
        path = self.backend / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)
        return path

    def call(self, name, event, stop_hook_active=False):
        payload = {
            "session_id": "extended",
            "turn_id": "turn-" + str(self.turn),
            "cwd": str(self.root),
            "hook_event_name": event,
            "stop_hook_active": stop_hook_active,
        }
        result = subprocess.run(
            [sys.executable, str(HOOKS / name)],
            input=json.dumps(payload), text=True, capture_output=True,
            env=self.env, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def check_case(self, name, relative, good, bad, diagnostic):
        file = self.put(relative, good)
        self.turn += 1
        self.assertEqual(self.call("detect-changes.py", "UserPromptSubmit"), {})
        self.put(relative, good + "\n// test modification\n")
        self.assertEqual(self.call("validate-" + name + ".py", "Stop"), {},
                         "Valid " + name + " should pass")
        self.turn += 1
        self.assertEqual(self.call("detect-changes.py", "UserPromptSubmit"), {})
        self.put(relative, bad)
        failure = self.call("validate-" + name + ".py", "Stop")
        self.assertEqual(failure.get("decision"), "block", str(failure))
        self.assertIn(diagnostic, failure["reason"])
        # Block loops are suppressed after Codex begins its Stop-hook correction.
        again = self.call("validate-" + name + ".py", "Stop", True)
        self.assertNotIn("decision", again)
        self.assertIn("systemMessage", again)
        return file

    def test_controller(self):
        good = """import { Controller, Get } from '@nestjs/common';
@Controller('users')
export class UserController {
  constructor(private readonly userService: UserService) {}
  @Get('list')
  @ApiOperation({ summary: 'Listar' })
  @ApiResponse({ status: 200, type: UserListDto })
  @ApiResponse({ status: 400, type: HttpErrorDto })
  @TraceNode({ name: 'list', type: 'controller' })
  list() { return this.userService.list(); }
}
"""
        bad = good.replace("list() { return this.userService.list(); }",
                           "list() { const x = 1; return this.userService.list(x); }")
        self.check_case("controller", "src/modules/user/user.controller.ts",
                        good, bad, "lógica de negocio")

    def test_service(self):
        good = """import { Injectable } from '@nestjs/common';
import { UserQuery } from '@queries/user/user.query';
@Injectable()
export class UserService {
  constructor(private readonly userQuery: UserQuery) {}
  async find() { return this.userQuery.find(); }
}
"""
        bad = good.replace("import { UserQuery }", "import { database } from '@db/connection.db';\nimport { UserQuery }")
        self.check_case("service", "src/modules/user/user.service.ts",
                        good, bad, "Queries")

    def test_module(self):
        good = """import { Module } from '@nestjs/common';
@Module({ controllers: [UserController], providers: [UserService] })
export class UserModule {}
"""
        bad = good.replace("export class UserModule", "export class WrongModule")
        self.check_case("module", "src/modules/user/user.module.ts",
                        good, bad, "UserModule")

    def test_dto_multiple_classes_in_one_file(self):
        good = """import { Trace } from 'traceflow';
@Trace({ type: 'validation' })
export class UserListFiltersDto { page: number; }
@Trace({ type: 'validation' })
export class UserListDto { data: unknown[]; }
"""
        bad = good.replace("class UserListDto", "class UserList")
        self.check_case("dto", "src/modules/user/dto/user-list.dto.ts",
                        good, bad, "terminar en Dto")

    def test_function(self):
        good = """export class StringFunction {
  static capitalize(value: string) { return value.toUpperCase(); }
}
"""
        bad = good.replace("  static capitalize", "  capitalize")
        self.check_case("function", "src/functions/string.function.ts",
                        good, bad, "static")

    def test_table_three_audit_fields(self):
        good = """import { pgTable, timestamp, serial } from 'drizzle-orm/pg-core';
export const user = pgTable('user', {
  id: serial('id').primaryKey(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
  deletedAt: timestamp('deleted_at'),
});
export type User = typeof user.$inferSelect;
export type UserDTO = typeof user.$inferInsert;
"""
        bad = good.replace("  deletedAt: timestamp('deleted_at'),\n", "")
        self.check_case("table", "src/db/tables/user.table.ts",
                        good, bad, "deletedAt")

    def test_seed(self):
        good = """import { database } from '@db/connection.db';
import { users } from '@db/tables/users.table';
export async function seedUsers() { return database.insert(users).values([]); }
"""
        bad = good.replace("import { users }", "import { admins } from '@db/tables/admins.table';\nimport { users }")
        self.check_case("seed", "src/seeds/users.seed.ts",
                        good, bad, "una sola tabla")

    def test_script(self):
        good = """import path from 'path';
const outputDir = path.resolve(process.cwd(), 'generated');
console.log(outputDir);
"""
        bad = good.replace("const outputDir =", "const password = 'supersecret123';\nconst outputDir =")
        self.check_case("script", "scripts/generate-api-types.ts",
                        good, bad, "credencial")

    def test_tsconfig_jsonc(self):
        good = """{
  // aliases
  "compilerOptions": {
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "paths": { "@db/*": ["src/db/*",], },
  },
}
"""
        bad = good.replace('"module": "nodenext"', '"module": "commonjs"')
        self.check_case("tsconfig", "tsconfig.json",
                        good, bad, "nodenext")

    def test_no_cross_type_validation(self):
        """One edited Controller must not wake the Query or Service rules."""
        p = self.put("src/modules/user/user.controller.ts", "@Controller() export class UserController {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        p.write_text("export class WrongController {}")
        self.assertEqual(self.call("validate-query.py", "Stop"), {})
        self.assertEqual(self.call("validate-service.py", "Stop"), {})
        self.assertEqual(self.call("validate-script.py", "Stop"), {})
        self.assertEqual(self.call("validate-controller.py", "Stop").get("decision"), "block")

    def test_frontend_tsconfig_excluded(self):
        frontend = self.root / "frontend"
        frontend.mkdir(parents=True)
        (frontend / "src").mkdir()
        (frontend / "tsconfig.json").write_text('{"compilerOptions":{"module":"esnext"}}')
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        (frontend / "tsconfig.json").write_text('{"compilerOptions":{"module":"commonjs"}}')
        self.assertEqual(self.call("validate-tsconfig.py", "Stop"), {})


if __name__ == "__main__":
    unittest.main()
