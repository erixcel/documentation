"""Contrato interno de legibilidad: una función principal orquesta reglas privadas."""
import ast
import re
import unittest
from pathlib import Path


VALIDATORS = Path(__file__).resolve().parents[1] / "hooks" / "validators"
ENTRYPOINTS = {
    "controller": ("validate_controller", 6),
    "core": ("validate_core", 7),
    "dto": ("validate_dto", 5),
    "functions": ("validate_function", 7),
    "module": ("validate_module", 6),
    "query": ("validate_query", 4),
    "script": ("validate_script", 3),
    "seed": ("validate_seed", 6),
    "service": ("validate_service", 7),
    "table": ("validate_table", 5),
    "tsconfig": ("validate_tsconfig", 4),
}


class ValidatorRuleStructureTests(unittest.TestCase):
    def test_main_validator_is_first_function_and_rules_follow_it(self):
        for filename, (entrypoint, expected_count) in ENTRYPOINTS.items():
            with self.subTest(validator=filename):
                source = (VALIDATORS / (filename + ".py")).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=filename + ".py")
                functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
                self.assertGreaterEqual(len(functions), 2)
                self.assertEqual(functions[0].name, entrypoint)
                self.assertTrue(all(node.lineno > functions[0].lineno for node in functions[1:]))
                rule_numbers = [
                    int(number) for number in re.findall(r"(?m)^\s*# Regla (\d+):", source)
                ]
                self.assertEqual(rule_numbers, list(range(1, expected_count + 1)))
                helper_names = {node.name for node in functions[1:]}
                # Every validator must actually delegate to independent rule helpers.
                calls = {
                    node.func.id
                    for node in ast.walk(functions[0])
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                }
                self.assertTrue(calls & helper_names)
                self.assertGreaterEqual(len(calls & helper_names), min(2, expected_count))

    def test_existing_dto_organization_remains_unchanged(self):
        tree = ast.parse((VALIDATORS / "dto.py").read_text(encoding="utf-8"))
        funcs = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual(
            funcs,
            [
                "validate_dto",
                "_validate_dto_filename",
                "_validate_dto_classes",
                "_validate_dto_traces",
                "_validate_dto_database_imports",
                "_validate_dto_database_queries",
            ],
        )


if __name__ == "__main__":
    unittest.main()
