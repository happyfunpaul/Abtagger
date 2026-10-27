import shutil
import tempfile
import unittest
from pathlib import Path

import page
import settings


class TestSettings(unittest.TestCase):
    def setUp(self):
        self._old_path = settings.CONFIG_PATH
        self.dir = Path(tempfile.mkdtemp())
        settings.CONFIG_PATH = self.dir / "config.json"

    def tearDown(self):
        settings.CONFIG_PATH = self._old_path
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_default_template_matches_readme(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        self.assertEqual(settings.load()["rename_template"], settings.DEFAULT_RENAME_TEMPLATE)
        self.assertIn(settings.DEFAULT_RENAME_TEMPLATE, readme)

    def test_blank_template_falls_back_to_default(self):
        settings.CONFIG_PATH.write_text('{"rename_template": "   "}', encoding="utf-8")
        self.assertEqual(settings.load()["rename_template"], settings.DEFAULT_RENAME_TEMPLATE)

    def test_save_blank_template_keeps_default(self):
        settings.save({"rename_template": ""})
        self.assertEqual(settings.load()["rename_template"], settings.DEFAULT_RENAME_TEMPLATE)

    def test_page_uses_default_template(self):
        self.assertIn(settings.DEFAULT_RENAME_TEMPLATE, page.PAGE)
        self.assertNotIn("__DEFAULT_RENAME_TEMPLATE__", page.PAGE)


if __name__ == "__main__":
    unittest.main()
