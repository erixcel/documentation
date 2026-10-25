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
        self.put("src/modules/user/dto/list.dto.ts", "export class ListDto {}")
        self.check_case("controller", "src/modules/user/user.controller.ts",
                        good, bad, "lógica de negocio")

    def test_controller_methods_match_dto_folder_exactly(self):
        good = """@Controller('admin/auth')
export class AuthController {
  constructor(private readonly service: AuthService) {}
  @Post('login')
  @ApiOperation({ summary: 'Login' })
  @ApiResponse({ status: 200, type: LoginDto })
  @ApiResponse({ status: 400, type: HttpErrorDto })
  @TraceNode({ name: 'login', type: 'controller' })
  login() { return this.service.login(); }

  @Get('me')
  @ApiOperation({ summary: 'Current user' })
  @ApiResponse({ status: 200, type: MeDto })
  @ApiResponse({ status: 400, type: HttpErrorDto })
  @TraceNode({ name: 'me', type: 'controller' })
  me() { return this.service.me(); }
}
"""
        controller = "src/modules/admin/modules/auth/auth.controller.ts"
        self.put(controller, good)
        self.put("src/modules/admin/modules/auth/dto/login.dto.ts", "export class LoginDto {}")
        self.put("src/modules/admin/modules/auth/dto/me.dto.ts", "export class MeDto {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(controller, good + "\n// touched\n")
        self.assertEqual(self.call("validate-controller.py", "Stop"), {})

        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put("src/modules/admin/modules/auth/dto/auth.dto.ts", "export class AuthDto {}")
        extra = self.call("validate-controller.py", "Stop")
        self.assertEqual(extra.get("decision"), "block")
        self.assertIn("auth.dto.ts", extra["reason"])
        self.assertIn("sobrantes", extra["reason"])

        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        (self.backend / "src/modules/admin/modules/auth/dto/me.dto.ts").unlink()
        missing = self.call("validate-controller.py", "Stop")
        self.assertEqual(missing.get("decision"), "block")
        self.assertIn("me.dto.ts", missing["reason"])
        self.assertIn("faltantes", missing["reason"])

    def test_controller_camel_case_dto_name(self):
        code = """@Controller('users')
export class UserController {
  @Get('find-all')
  @ApiOperation({})
  @ApiResponse({ status: 200 })
  @ApiResponse({ status: 400 })
  @TraceNode({ name: 'findAll', type: 'controller' })
  findAll() { return this.userService.findAll(); }
}"""
        controller = "src/modules/user/user.controller.ts"
        self.put(controller, code)
        self.put("src/modules/user/dto/find-all.dto.ts", "export class FindAllDto {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(controller, code + "\n// touched\n")
        self.assertEqual(self.call("validate-controller.py", "Stop"), {})

    def test_controllers_in_same_folder_merge_dto_names(self):
        a = """@Controller('a')
export class AController {
  @Get()
  @ApiOperation({})
  @ApiResponse({ status: 200 })
  @ApiResponse({ status: 400 })
  @TraceNode({ name: 'find', type: 'controller' })
  find() { return this.aService.find(); }
}"""
        b = """@Controller('b')
export class BController {
  @Get()
  @ApiOperation({})
  @ApiResponse({ status: 200 })
  @ApiResponse({ status: 400 })
  @TraceNode({ name: 'list', type: 'controller' })
  list() { return this.bService.list(); }
}"""
        self.put("src/modules/team/a.controller.ts", a)
        self.put("src/modules/team/b.controller.ts", b)
        self.put("src/modules/team/dto/find.dto.ts", "export class FindDto {}")
        self.put("src/modules/team/dto/list.dto.ts", "export class ListDto {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put("src/modules/team/a.controller.ts", a + "\n// changed\n")
        self.assertEqual(self.call("validate-controller.py", "Stop"), {})

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
        self.put("src/modules/user/user.controller.ts", "export class UserController {}")
        self.put("src/modules/user/user.service.ts", "export class UserService {}")
        self.check_case("module", "src/modules/user/user.module.ts",
                        good, bad, "UserModule")

    def test_parent_module_rejects_loose_child_submodules(self):
        parent = "src/modules/admin/admin.module.ts"
        self.put(parent, "@Module({}) export class AdminModule {}")
        self.put("src/modules/admin/administrators/administrators.module.ts",
                 "@Module({}) export class AdministratorsModule {}")
        self.put("src/modules/admin/auth/auth.module.ts",
                 "@Module({}) export class AuthModule {}")
        self.put("src/modules/admin/functions/helper.function.ts", "export class HelperFunction {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(parent, "@Module({ imports: [] }) export class AdminModule {}")
        result = self.call("validate-module.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("administrators/", result["reason"])
        self.assertIn("auth/", result["reason"])
        self.assertIn("modules/<nombre>/<nombre>.module.ts", result["reason"])

    def test_child_module_rejects_old_nested_location(self):
        child = "src/modules/admin/auth/auth.module.ts"
        self.put("src/modules/admin/admin.module.ts", "@Module({}) export class AdminModule {}")
        self.put(child, "@Module({}) export class AuthModule {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(child, "@Module({ providers: [] }) export class AuthModule {}")
        result = self.call("validate-module.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("admin/modules/auth/auth.module.ts", result["reason"])

    def test_grouped_submodules_are_valid(self):
        parent = "src/modules/admin/admin.module.ts"
        self.put(parent, "@Module({}) export class AdminModule {}")
        self.put("src/modules/admin/modules/auth/auth.module.ts",
                 "@Module({}) export class AuthModule {}")
        self.put("src/modules/admin/modules/auth/modules/session/session.module.ts",
                 "@Module({}) export class SessionModule {}")
        self.put("src/modules/admin/dto/admin.dto.ts", "export class AdminDto {}")
        self.put("src/modules/admin/functions/trace.function.ts",
                 "export class TraceFunction { static start() {} }")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(parent, "@Module({ imports: [] }) export class AdminModule {}")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_new_ungrouped_child_triggers_parent_without_edit(self):
        parent = "src/modules/admin/admin.module.ts"
        self.put(parent, "@Module({}) export class AdminModule {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put("src/modules/admin/contributions/contributions.module.ts",
                 "@Module({}) export class ContributionsModule {}")
        result = self.call("validate-module.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("contributions/", result["reason"])

    def test_root_main_modules_are_exempt_from_grouping_requirement(self):
        admin = "src/modules/admin/admin.module.ts"
        bettor = "src/modules/bettor/bettor.module.ts"
        public = "src/modules/public/public.module.ts"
        for path, name in ((admin, "Admin"), (bettor, "Bettor"), (public, "Public")):
            self.put(path, f"@Module({{}}) export class {name}Module {{}}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(admin, "@Module({ imports: [] }) export class AdminModule {}")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_wrong_name_or_direct_file_in_modules_group_rejected(self):
        wrong = "src/modules/admin/modules/users/customer.module.ts"
        self.put(wrong, "@Module({}) export class CustomerModule {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(wrong, "@Module({ imports: [] }) export class CustomerModule {}")
        result = self.call("validate-module.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("carpeta del módulo debe llamarse", result["reason"])

    def test_module_exact_trio_with_subfolders(self):
        path = "src/modules/admin/modules/auth/auth.module.ts"
        code = "@Module({}) export class AuthModule {}"
        self.put(path, code)
        self.put("src/modules/admin/modules/auth/auth.controller.ts", "class AuthController {}")
        self.put("src/modules/admin/modules/auth/auth.service.ts", "class AuthService {}")
        self.put("src/modules/admin/modules/auth/functions/token.function.ts",
                 "class TokenFunction { static create() {} }")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(path, code + "\n// touch")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_module_wrong_sibling_name_even_when_optional(self):
        path = "src/modules/admin/modules/auth/auth.module.ts"
        self.put(path, "@Module({}) export class AuthModule {}")
        self.put("src/modules/admin/modules/auth/session.service.ts", "class SessionService {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(path, "@Module({}) export class AuthModule {}\n// touch")
        out = self.call("validate-module.py", "Stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("session.service.ts", out["reason"])
        self.assertNotIn("Faltan archivos", out["reason"])

    def test_module_extra_service_triggers_without_editing_module(self):
        path = "src/modules/bettor/modules/auth/auth.module.ts"
        self.put(path, "@Module({}) export class AuthModule {}")
        self.put("src/modules/bettor/modules/auth/auth.controller.ts", "class AuthController {}")
        self.put("src/modules/bettor/modules/auth/auth.service.ts", "class AuthService {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put("src/modules/bettor/modules/auth/google-auth.service.ts", "class GoogleAuthService {}")
        out = self.call("validate-module.py", "Stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("google-auth.service.ts", out["reason"])

    def test_module_extra_config_file_triggers_without_editing_module(self):
        path = "src/modules/admin/modules/auth/auth.module.ts"
        self.put(path, "@Module({}) export class AuthModule {}")
        self.put("src/modules/admin/modules/auth/auth.controller.ts", "class AuthController {}")
        self.put("src/modules/admin/modules/auth/auth.service.ts", "class AuthService {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put("src/modules/admin/modules/auth/jwt.config.ts", "export const jwtConfig = {};")
        out = self.call("validate-module.py", "Stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("jwt.config.ts", out["reason"])

    def test_module_removing_optional_service_does_not_block(self):
        path = "src/modules/admin/modules/auth/auth.module.ts"
        self.put(path, "@Module({}) export class AuthModule {}")
        self.put("src/modules/admin/modules/auth/auth.controller.ts", "class AuthController {}")
        service = self.put("src/modules/admin/modules/auth/auth.service.ts", "class AuthService {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        service.unlink()
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_module_only_module_without_controller_or_service(self):
        name = "src/modules/admin/admin.module.ts"
        self.put(name, "@Module({ imports: [] }) export class AdminModule {}")
        self.put("src/modules/admin/modules/auth/auth.module.ts", "@Module({}) export class AuthModule {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(name, "@Module({ imports: [AuthModule] }) export class AdminModule {}")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_module_optional_service_only(self):
        name = "src/modules/admin/modules/auth/auth.module.ts"
        self.put(name, "@Module({}) export class AuthModule {}")
        self.put("src/modules/admin/modules/auth/auth.service.ts", "class AuthService {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(name, "@Module({ providers: [AuthService] }) export class AuthModule {}")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_module_optional_controller_only(self):
        name = "src/modules/admin/modules/health/health.module.ts"
        self.put(name, "@Module({}) export class HealthModule {}")
        self.put("src/modules/admin/modules/health/health.controller.ts", "class HealthController {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(name, "@Module({ controllers: [HealthController] }) export class HealthModule {}")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_security_module_detects_existing_extra_siblings(self):
        path = "src/security/security.module.ts"
        self.put(path, "@Module({}) export class SecurityModule {}")
        self.put("src/security/session.service.ts", "class SessionService {}")
        self.put("src/security/auth.guard.ts", "class AuthGuard {}")
        self.put("src/security/jwt.config.ts", "export const jwtConfig = {};")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(path, "@Module({ providers: [SessionService] }) export class SecurityModule {}")
        result = self.call("validate-module.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        for name in ("session.service.ts", "auth.guard.ts", "jwt.config.ts"):
            self.assertIn(name, result["reason"])

    def test_security_sibling_creation_triggers_without_module_edits(self):
        path = "src/security/security.module.ts"
        self.put(path, "@Module({}) export class SecurityModule {}")
        self.put("src/security/security.service.ts", "class SecurityService {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put("src/security/session.service.ts", "class SessionService {}")
        result = self.call("validate-module.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("session.service.ts", result["reason"])

    def test_security_module_allows_only_module_and_folders(self):
        path = "src/security/security.module.ts"
        self.put(path, "@Module({}) export class SecurityModule {}")
        self.put("src/security/guards/auth.guard.ts", "class AuthGuard {}")
        self.put("src/security/dto/session.dto.ts", "class SessionDto {}")
        self.put("src/security/modules/session/session.module.ts", "@Module({}) export class SessionModule {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(path, "@Module({ imports: [SessionModule] }) export class SecurityModule {}")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_other_direct_src_module_except_app_uses_same_rule(self):
        name = "src/custom.module.ts"
        self.put(name, "@Module({}) export class CustomModule {}")
        self.put("src/extra.service.ts", "class ExtraService {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(name, "@Module({}) export class CustomModule {}\n// changed")
        result = self.call("validate-module.py", "Stop")
        self.assertEqual(result.get("decision"), "block")
        self.assertIn("extra.service.ts", result["reason"])

    def test_module_root_app_module_is_exempt(self):
        self.put("src/app.module.ts", "@Module({}) export class AppModule {}")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put("src/app.module.ts", "@Module({}) export class AppModule {}\n// changed")
        self.assertEqual(self.call("validate-module.py", "Stop"), {})

    def test_module_local_function_hook_runs(self):
        path = "src/modules/admin/modules/auth/functions/token.function.ts"
        self.put(path, "export class TokenFunction { static create() {} }")
        self.turn += 1
        self.call("detect-changes.py", "UserPromptSubmit")
        self.put(path, "export class TokenFunction { create() {} }")
        out = self.call("validate-function.py", "Stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("static", out["reason"])

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
        good = """import { TraceNode } from '@erixcel/traceflow';
export class StringFunction {
  @TraceNode({ name: 'string.capitalize', type: 'method' })
  static capitalize(value: string) { return value.toUpperCase(); }
}
"""
        bad = good.replace("  static capitalize", "  capitalize")
        self.check_case("function", "src/functions/string.function.ts",
                        good, bad, "static")

    def test_function_forbids_top_level_types(self):
        good = """import { TraceNode } from '@erixcel/traceflow';
export class FijaFunction {
  @TraceNode({ name: 'fija.run', type: 'method' })
  static run() {}
}
"""
        bad = "type Value = string;\ninterface Test { foo: number }\n" + good
        self.check_case("function", "src/functions/fija.function.ts", good, bad, "fuera de la clase")

    def test_function_forbids_top_level_consts_and_loose_functions(self):
        good = """import { TraceNode } from '@erixcel/traceflow';
export class FijaFunction {
  @TraceNode({ name: 'fija.run', type: 'method' })
  static run() {}
}
"""
        bad = "const value = 1;\nfunction extra() {}\n" + good
        self.check_case("function", "src/functions/fija.function.ts", good, bad, "fuera de la clase")

    def test_function_trace_required_for_each_method(self):
        good = """import { TraceNode } from '@erixcel/traceflow';
export class FijaFunction {
  @TraceNode({ name: 'fija.first', type: 'method' })
  static first() {}
  @TraceNode({ name: 'fija.second', type: 'method' })
  static second() {}
}
"""
        bad = good.replace("  @TraceNode({ name: 'fija.second', type: 'method' })\n", "")
        self.check_case("function", "src/functions/fija.function.ts", good, bad, "falta @TraceNode")

    def test_function_wrong_trace_type(self):
        good = """import { TraceNode } from '@erixcel/traceflow';
export class FijaFunction {
  @TraceNode({ name: 'fija.run', type: 'method' })
  static run() {}
}
"""
        self.check_case("function", "src/functions/fija.function.ts", good,
                        good.replace("type: 'method'", "type: 'controller'"), "type: 'method'")

    def test_function_legacy_import(self):
        good = """import { TraceNode } from '@erixcel/traceflow';
export class FijaFunction {
  @TraceNode({ name: 'fija.run', type: 'method' })
  static run() {}
}
"""
        self.check_case("function", "src/functions/fija.function.ts", good,
                        good.replace("from '@erixcel/traceflow'", "from 'traceflow'"), "@erixcel/traceflow")

    def test_function_all_methods_static(self):
        good = """import { TraceNode } from '@erixcel/traceflow';
export class FijaFunction {
  @TraceNode({ name: 'fija.first', type: 'method' })
  static first() {}
  @TraceNode({ name: 'fija.helper', type: 'method' })
  private static helper() {}
}
"""
        self.check_case("function", "src/functions/fija.function.ts", good,
                        good.replace("private static helper", "private helper"), "static")

    def test_function_generic_methods_must_be_traced(self):
        good = """import { TraceNode } from '@erixcel/traceflow';
export class StringFunction {
  @TraceNode({ name: 'string.clean', type: 'method' })
  static clean<T>(value: T): T { return value; }
  @TraceNode({ name: 'string.walk', type: 'method' })
  private static walk<T>(value: T): T { return value; }
}
"""
        bad = good.replace("  @TraceNode({ name: 'string.walk', type: 'method' })\n", "")
        self.check_case("function", "src/functions/string.function.ts", good,
                        bad, "falta @TraceNode")

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
