"""Keep the public hook directory unambiguous and free of legacy facades."""
import ast
import json
import re
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
LEGACY = {
    "validator_common",
    "extra_rules",
    "core_validator",
    "query_structure",
}


class HookRegistryTests(unittest.TestCase):
    def test_root_python_files_match_registered_hook_commands(self):
        config = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
        command_files = []
        for groups in config["hooks"].values():
            for group in groups:
                for entry in group["hooks"]:
                    command = entry["command"]
                    match = re.search(r"/hooks/([\w-]+\.py)", command)
                    self.assertIsNotNone(match, command)
                    command_files.append(match.group(1))
        root_scripts = {p.name for p in HOOKS.glob("*.py")}
        self.assertEqual(len(command_files), 12)
        self.assertEqual(len(set(command_files)), 12)
        self.assertEqual(root_scripts, set(command_files))
        self.assertEqual(
            {p.name for p in HOOKS.iterdir() if p.is_file()},
            root_scripts | {"hooks.json"},
        )

    def test_no_legacy_root_facade_imports(self):
        for name in LEGACY:
            self.assertFalse((HOOKS / f"{name}.py").exists(), name)
        for path in HOOKS.rglob("*.py"):
            with self.subTest(path=str(path.relative_to(HOOKS))):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        self.assertNotIn(node.module, LEGACY)
                    elif isinstance(node, ast.Import):
                        for item in node.names:
                            self.assertNotIn(item.name, LEGACY)


if __name__ == "__main__":
    unittest.main()
