import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("build_site", ROOT / "platform/publishing/build_site.py")
BUILD_SITE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILD_SITE)


class SiteBuildTests(unittest.TestCase):
    def test_review_build_contains_all_issues_and_noindex(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            count = BUILD_SITE.write_site(output, include_drafts=True)
            self.assertEqual(count, 4)
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("Закрытый предпросмотр", index)
            self.assertIn('name="robots" content="noindex,nofollow"', index)
            for number in range(1, 5):
                issue = f"issue-{number:03d}"
                metadata = json.loads(
                    (Path(__file__).resolve().parents[2] / f"productions/issues/{issue}/issue.json").read_text(encoding="utf-8")
                )
                self.assertIn(metadata["title"], index)
                self.assertTrue((output / f"assets/comics/{issue}.png").exists())
            characters = (output / "characters/index.html").read_text(encoding="utf-8")
            self.assertIn("Картотека", characters)
            self.assertIn("Даня", characters)
            self.assertIn("NEYRA", characters)
            self.assertIn("Мы же не договорились", characters)
            self.assertIn('name="robots" content="noindex,nofollow"', characters)

    def test_public_build_excludes_unpublished_issues(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            count = BUILD_SITE.write_site(output, include_drafts=False)
            self.assertEqual(count, 0)
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("Закрытый предпросмотр", index)
            self.assertIn("Первый выпуск готовится", index)
            characters = (output / "characters/index.html").read_text(encoding="utf-8")
            self.assertIn("Даня", characters)
            self.assertIn("Курьер-дрон Гриша", characters)
            self.assertNotIn("Мы же не договорились", characters)
            self.assertNotIn("/comics/issue-001", characters)
            self.assertIn("GENERATED FILE", characters)


if __name__ == "__main__":
    unittest.main()
