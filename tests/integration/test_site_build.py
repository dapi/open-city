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
            self.assertIn('/news/municipal-os-site-direction/', index)
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
            self.assertIn("Прямой взгляд, узнаваемый magenta-силуэт", characters)
            self.assertIn("/assets/characters/neyra-portrait-v1.png", characters)
            portrait_names = {
                "danya-portrait-v1.png",
                "flepik-portrait-v1.png",
                "marina-portrait-v1.png",
                "mayor-chatbot-portrait-v1.png",
                "grisha-portrait-v1.png",
                "neyra-portrait-v1.png",
                "max-hypestein-portrait-v1.png",
            }
            for portrait_name in portrait_names:
                self.assertIn(f"/assets/characters/{portrait_name}", characters)
                self.assertTrue((output / "assets/characters" / portrait_name).is_file())
            self.assertIn("Архивные варианты · 3", characters)
            self.assertIn("/assets/characters/archive/flepik-01.png", characters)
            self.assertLess(
                characters.index("/assets/characters/archive/flepik-03.png"),
                characters.index("/assets/characters/archive/flepik-01.png"),
            )
            self.assertTrue((output / "assets/characters/archive/flepik-01.png").is_file())
            self.assertTrue((output / "assets/characters/archive/grisha-03.png").is_file())
            self.assertFalse((output / "assets/characters/archive/grisha-01.png").exists())
            self.assertFalse((output / "assets/characters/archive/mayor-chatbot-02.png").exists())
            archive = (output / "archive/index.html").read_text(encoding="utf-8")
            archive_manifest = json.loads((output / "archive/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(archive_manifest), 47)
            self.assertEqual(archive_manifest[0]["id"], "ARCH-047")
            self.assertEqual(archive_manifest[0]["appearance_date"], "2026-08-10")
            self.assertIn("ARCH-001", archive)
            self.assertLess(archive.index("ARCH-047"), archive.index("ARCH-001"))
            self.assertIn("Сначала показаны самые новые изображения", archive)
            self.assertIn("Friendly_Robot_with_Glowing_Antenna.png", archive)
            self.assertIn("Появился: 2025-11-03", archive)
            self.assertNotIn("knowledge/sources/chatgpt", archive)
            self.assertIn("/assets/archive/arch-001.png", archive)
            self.assertTrue((output / "assets/archive/arch-001.png").is_file())
            self.assertTrue((output / "assets/archive/arch-045.png").is_file())
            self.assertTrue((output / "assets/archive/arch-047.png").is_file())
            self.assertTrue((output / "assets/archive/arch-050.png").is_file())
            for removed_id in ("010", "022", "046"):
                self.assertNotIn(f"ARCH-{removed_id}", archive)
                self.assertFalse((output / f"assets/archive/arch-{removed_id}.png").exists())
            self.assertNotIn("Screenshot_2025-11-02_at_21.35.49.png", archive)
            self.assertNotIn("f2f54056-f7a4-438c-a818-1393f4162cb7.png", archive)
            self.assertNotIn("ca76c594-8f40-4be1-9400-9321f45f01a3.png", archive)
            self.assertNotIn("75d0077e-defa-484f-bc6c-f751fcb4e7aa.png", archive)
            self.assertNotIn("source_path", json.dumps(archive_manifest, ensure_ascii=False))
            styles = (output / "assets/styles.css").read_text(encoding="utf-8")
            header_styles = (output / "assets/site-header.css").read_text(encoding="utf-8")
            self.assertIn(".archive-grid { display: grid; grid-template-columns: repeat(2", styles)
            self.assertIn(".archive-hero h1 { font-size: clamp(2.6rem", styles)
            self.assertIn(".dashboard {", styles)
            self.assertIn(".issue-feature-grid { grid-template-columns: 1fr; }", styles)
            self.assertIn(".archive-grid { grid-template-columns: 1fr; }", styles)
            self.assertIn("overflow-x: auto", header_styles)
            self.assertIn("repeat(5, minmax(104px, 1fr))", header_styles)
            news_index = (output / "news/index.html").read_text(encoding="utf-8")
            news_article = (
                output / "news/color-breath-first-reference-pack/index.html"
            ).read_text(encoding="utf-8")
            site_direction_article = (
                output / "news/municipal-os-site-direction/index.html"
            ).read_text(encoding="utf-8")
            self.assertIn("Новости студии", news_index)
            self.assertIn("Color-Breath: первый пакет", news_index)
            self.assertIn("Сайт становится муниципальной ОС", news_index)
            self.assertIn("Принципы Color-Breath", news_article)
            self.assertIn("Следить за процессом", news_article)
            self.assertIn('class="studio-mark"', news_article)
            self.assertIn('class="site-nav"', news_article)
            self.assertNotIn('class="nav-links"', news_article)
            self.assertIn('href="/archive/"><span class="nav-index">05</span>Архив</a>', news_article)
            self.assertIn('/assets/site-header.css', news_article)
            self.assertIn('id="news-lightbox"', news_article)
            self.assertEqual(news_article.count("data-lightbox data-caption="), 9)
            self.assertEqual(news_article.count('class="news-gallery-item"'), 8)
            self.assertTrue((output / "assets/news-lightbox.js").is_file())
            self.assertTrue((output / "assets/home-shell.js").is_file())
            self.assertTrue((output / "assets/site-header.css").is_file())
            self.assertTrue(
                (
                    output
                    / "assets/news/color-breath-first-reference-pack/08-max-hypestein-model-sheet-v1.png"
                ).is_file()
            )
            self.assertIn("Четыре направления сайта", site_direction_article)
            self.assertEqual(
                site_direction_article.count('class="news-gallery-item"'), 4
            )
            self.assertTrue(
                (
                    output
                    / "assets/news/municipal-os-site-direction/04-city-map-page-candidate-v1.png"
                ).is_file()
            )
            city = (output / "city/index.html").read_text(encoding="utf-8")
            studio = (output / "studio/index.html").read_text(encoding="utf-8")
            self.assertIn("Городские разделы", city)
            self.assertIn("СПИСОЧНАЯ АЛЬТЕРНАТИВА", city)
            self.assertIn('href="/city/" aria-current="page"', city)
            self.assertIn("Производственный маршрут", studio)
            self.assertIn('href="/studio/" aria-current="page"', studio)
            self.assertTrue((output / "assets/site/city-map-concept.png").is_file())
            self.assertIn('class="home-screen"', index)
            self.assertIn('class="home-console shell"', index)
            self.assertIn('role="tablist"', index)
            self.assertEqual(index.count('data-home-tab='), 5)
            self.assertLess(index.index('id="home-panel-issues"'), index.index('id="home-panel-city"'))
            self.assertIn('/assets/home-shell.js', index)
            self.assertIn('name="robots" content="noindex,nofollow"', characters)
            self.assertFalse(any(line.endswith(" ") for line in characters.splitlines()))
            self.assertFalse(any(line.endswith(" ") for line in news_article.splitlines()))

    def test_public_build_excludes_unpublished_issues(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            count = BUILD_SITE.write_site(output, include_drafts=False)
            self.assertEqual(count, 0)
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("Закрытый предпросмотр", index)
            self.assertIn("Первый выпуск готовится", index)
            news_article = output / "news/color-breath-first-reference-pack/index.html"
            self.assertTrue(news_article.is_file())
            self.assertNotIn(
                "Закрытый предпросмотр", news_article.read_text(encoding="utf-8")
            )
            characters = (output / "characters/index.html").read_text(encoding="utf-8")
            self.assertIn("Даня", characters)
            self.assertIn("Курьер-дрон Гриша", characters)
            self.assertNotIn("Мы же не договорились", characters)
            self.assertNotIn("/comics/issue-001", characters)
            self.assertIn("GENERATED FILE", characters)


if __name__ == "__main__":
    unittest.main()
