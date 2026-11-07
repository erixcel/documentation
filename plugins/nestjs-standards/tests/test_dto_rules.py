"""Regresión de las reglas independientes de DTO (sin NestJS en ejecución)."""
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from validators.dto import validate_dto  # noqa: E402


class DtoRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def validate(self, code, name="user-list.dto.ts"):
        file = self.folder / name
        file.write_text(code, encoding="utf-8")
        return validate_dto(file)

    def test_valid_dto_with_two_classes(self):
        source = """import { Trace } from 'traceflow';
@Trace({ type: 'validation' })
export class UserListFiltersDto { page: number; }
@Trace({ type: 'validation' })
export class UserListDto { data: unknown[]; }
"""
        self.assertEqual(self.validate(source), [])

    def test_rule_1_filename(self):
        source = "@Trace({ type: 'validation' }) export class UserDto {}"
        self.assertEqual(
            self.validate(source, "UserList.dto.ts"),
            ["Nombre de DTO: kebab-case y sufijo .dto.ts."],
        )

    def test_rule_2_class_required_and_suffix(self):
        self.assertEqual(
            self.validate("export const sample = 1;"),
            ["El DTO debe declarar una o más clases."],
        )
        self.assertEqual(
            self.validate("@Trace({ type: 'validation' }) export class User {}"),
            ["La clase User debe terminar en Dto."],
        )

    def test_rule_3_trace_for_each_class(self):
        source = """@Trace({ type: 'validation' }) export class FirstDto {}
export class SecondDto {}
"""
        self.assertEqual(
            self.validate(source),
            ["Cada clase DTO debe llevar @Trace({ type: 'validation' })."],
        )

    def test_rule_4_database_imports(self):
        source = """import { UserQuery } from '@queries/user/user.query';
@Trace({ type: 'validation' }) export class UserDto {}
"""
        self.assertEqual(
            self.validate(source),
            ["Los DTO no deben consultar la base de datos ni depender de su conexión."],
        )

    def test_rule_5_direct_database_queries(self):
        source = """@Trace({ type: 'validation' })
export class UserDto {
  getData() { return db.select(); }
}
"""
        self.assertEqual(
            self.validate(source),
            ["Las consultas no pertenecen a los DTO."],
        )

    def test_rules_report_all_errors_without_early_exit(self):
        source = """import { UserQuery } from '@queries/user/user.query';
export class User {
  run() { return database.insert(); }
}
"""
        self.assertEqual(
            self.validate(source, "User.dto.ts"),
            [
                "Nombre de DTO: kebab-case y sufijo .dto.ts.",
                "La clase User debe terminar en Dto.",
                "Cada clase DTO debe llevar @Trace({ type: 'validation' }).",
                "Los DTO no deben consultar la base de datos ni depender de su conexión.",
                "Las consultas no pertenecen a los DTO.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
