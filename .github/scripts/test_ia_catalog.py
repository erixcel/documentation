#!/usr/bin/env python3
"""Regression checks for separate Mintlify catalogs per Codex plugin."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = {
    "nestjs": {"plugin": "nestjs-standards", "skills": 9, "hooks": 12, "opposite": "react-standards"},
    "react": {"plugin": "react-standards", "skills": 15, "hooks": 13, "opposite": "nestjs-standards"},
}


class CatalogIsolationTests(unittest.TestCase):
    def test_navigation_has_clickable_expandable_plugin_groups(self):
        config = json.loads((ROOT / "docs.json").read_text(encoding="utf-8"))
        ia = next(tab for tab in config["navigation"]["tabs"] if tab.get("tab") == "IA")
        groups = [group for section in ia["groups"] for group in section["pages"]]
        self.assertEqual([group["group"] for group in groups], ["NestJS", "React"])
        for slug, label in (("nestjs", "NestJS"), ("react", "React")):
            group = next(x for x in groups if x["group"] == label)
            self.assertEqual(group.get("root"), "ia/" + slug)
            self.assertEqual(group.get("directory"), "card")
            self.assertEqual(group["pages"], ["ia/" + slug + "/skills", "ia/" + slug + "/hooks"])
            self.assertTrue((ROOT / "ia" / (slug + ".mdx")).is_file())

    def test_catalogs_are_independent(self):
        for slug, info in SPECS.items():
            with self.subTest(plugin=slug):
                root = ROOT / "ia" / slug
                for section, expected in (("skills", info["skills"]), ("hooks", info["hooks"])):
                    content = (root / (section + ".mdx")).read_text(encoding="utf-8")
                    self.assertIn(
                        ("Skills disponibles" if section == "skills" else "Hooks por evento")
                        + " (" + str(expected) + ")",
                        content,
                    )
                    cards = re.findall(r'<Card title="[^"]+" icon="[^"]+" href="([^"]+)"', content)
                    self.assertEqual(len(cards), expected)
                    self.assertTrue(all("/plugins/" + info["plugin"] + "/" in url for url in cards))
                    self.assertTrue(all("/plugins/" + info["opposite"] + "/" not in url for url in cards))
                intro = (ROOT / "ia" / (slug + ".mdx")).read_text(encoding="utf-8")
                self.assertIn("href=\"/ia/" + slug + "/skills\"", intro)
                self.assertIn("href=\"/ia/" + slug + "/hooks\"", intro)
                self.assertIn("erixcel/documentation", intro)

    def test_plugins_remain_independent(self):
        market = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        sources = {
            item["name"]: item["source"]["path"]
            for item in market["plugins"]
        }
        self.assertEqual(sources["nestjs-standards"], "./plugins/nestjs-standards")
        self.assertEqual(sources["react-standards"], "./plugins/react-standards")
        for slug, info in SPECS.items():
            root = ROOT / "plugins" / info["plugin"]
            self.assertEqual(len(list((root / "skills").glob("*/SKILL.md"))), info["skills"])
            cfg = json.loads((root / "hooks/hooks.json").read_text())
            total = sum(len(group["hooks"]) for groups in cfg["hooks"].values() for group in groups)
            self.assertEqual(total, info["hooks"])

    def test_legacy_urls_are_chooser_pages(self):
        for name in ("skills", "hooks"):
            content = (ROOT / "ia" / (name + ".mdx")).read_text(encoding="utf-8")
            self.assertIn("/ia/react/" + name, content)
            self.assertIn("/ia/nestjs/" + name, content)
            self.assertNotIn("/plugins/nestjs-standards/skills/", content)
            self.assertNotIn("/plugins/react-standards/skills/", content)


if __name__ == "__main__":
    unittest.main()
