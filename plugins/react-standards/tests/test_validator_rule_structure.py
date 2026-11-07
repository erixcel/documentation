"""La estructura de los validadores React debe reflejar reglas independientes."""
import ast
import re
import unittest
from pathlib import Path


VALIDATORS = Path(__file__).resolve().parents[1] / "hooks" / "validators"
ENTRYPOINTS = {
    "api": ("validate_api", 3),
    "components": ("validate_components", 6),
    "config": ("validate_config", 9),
    "functions": ("validate_functions", 4),
    "hooks": ("validate_hooks", 2),
    "interfaces": ("validate_interfaces", 2),
    "layouts": ("validate_layout_files", 3),
    "main": ("validate_main", 3),
    "pages": ("validate_page_files", 5),
    "routes": ("validate_routes", 3),
    "services": ("validate_services", 3),
    "stores": ("validate_stores", 4),
    "structure": ("validate_structure", 3),
    "styles": ("validate_styles", 3),
}


class ReactValidatorRuleStructureTests(unittest.TestCase):
    def test_numbered_rules_and_private_helpers(self):
        for filename, (entrypoint, count) in ENTRYPOINTS.items():
            with self.subTest(module=filename):
                source = (VALIDATORS / (filename + ".py")).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=filename + ".py")
                functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
                self.assertGreaterEqual(len(functions), 2)
                self.assertEqual(functions[0].name, entrypoint)

                labels = re.findall(r"(?m)^\s*# Regla (\d+):\s*\S", source)
                self.assertEqual([int(label) for label in labels], list(range(1, count + 1)))
                helpers = {node.name for node in functions[1:] if node.name.startswith("_validate_")}
                self.assertGreaterEqual(len(helpers), 2)

                # Las reglas de los orquestadores deben llamar a sus helpers reales.
                calls = {
                    node.func.id
                    for node in ast.walk(functions[0])
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                }
                self.assertGreaterEqual(len(calls & helpers), 2)

    def test_legacy_entrypoints_remain_importable(self):
        expected = {
            "pages": {"validate_page_files", "validate_pages", "validate_page_routes", "page_roots"},
            "services": {"validate_services", "validate_api_services"},
            "config": {"validate_config", "env_keys"},
            "stores": {"validate_stores", "is_store_path"},
        }
        for module, names in expected.items():
            with self.subTest(module=module):
                source = (VALIDATORS / (module + ".py")).read_text(encoding="utf-8")
                tree = ast.parse(source)
                actual = {
                    node.name for node in tree.body if isinstance(node, ast.FunctionDef)
                }
                self.assertTrue(names.issubset(actual), names - actual)


if __name__ == "__main__":
    unittest.main()
