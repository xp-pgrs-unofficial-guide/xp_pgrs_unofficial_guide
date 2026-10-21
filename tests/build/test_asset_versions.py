"""Render-time stylesheet versions must survive cached Pages assets safely."""

from contextlib import redirect_stdout
import hashlib
from html.parser import HTMLParser
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import build


class StylesheetHTML(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            self.links.append(dict(attrs))


class AssetVersionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.book = Path(temporary.name) / "book"
        self.output = self.book / "_book"
        self.output.mkdir(parents=True)
        self.css = self.book / "assets/guide.css"
        self.css.parent.mkdir()
        self.css.write_text(".guide-profile-link { color: teal; }\n", encoding="utf-8")
        for name, value in (("BOOK", self.book), ("OUTPUT", self.output)):
            patcher = patch.object(build, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def article(self, relative, html):
        source = self.book / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("fixture", encoding="utf-8")
        target = self.output / Path(relative).with_suffix(".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        return target

    def version(self):
        with redirect_stdout(io.StringIO()):
            return build.version_stylesheets()

    def digest(self):
        return hashlib.sha1(self.css.read_bytes()).hexdigest()

    def test_chinese_and_english_articles_keep_their_relative_paths(self):
        sources = {"index.qmd": "assets/guide.css", "authors/person.qmd": "../assets/guide.css",
                   "en/index.qmd": "../assets/guide.css", "en/authors/person.qmd": "../../assets/guide.css"}
        outputs = [self.article(source, f'<link rel="stylesheet" href="{href}">')
                   for source, href in sources.items()]
        self.assertEqual(self.version(), 4)
        for target, href in zip(outputs, sources.values()):
            self.assertEqual(StylesheetHTML(target.read_text()).links[0]["href"], href + "?v=" + self.digest())

    def test_only_local_reader_stylesheet_links_change(self):
        unchanged = '\n'.join([
            '<link rel="stylesheet" href="https://cdn.example/assets/guide.css">',
            '<link rel="stylesheet" href="//cdn.example/assets/guide.css">',
            '<link rel="stylesheet" href="assets/other.css">',
            '<link rel="preload" href="assets/guide.css">',
            '<script src="assets/guide.css"></script><img src="assets/guide.css">',
            '<!-- <link rel="stylesheet" href="assets/guide.css"> -->',
            '<script>const example = \'<link rel="stylesheet" href="assets/guide.css">\';</script>',
        ])
        target = self.article("index.qmd", unchanged + '\n<link rel="stylesheet" href="assets/guide.css">')
        extra = self.output / "unregistered.html"
        extra.write_text('<link rel="stylesheet" href="assets/guide.css">', encoding="utf-8")
        self.assertEqual(self.version(), 1)
        self.assertTrue(target.read_text().startswith(unchanged + "\n"))
        self.assertEqual(extra.read_text(), '<link rel="stylesheet" href="assets/guide.css">')

    def test_existing_parameters_fragments_and_html_escaping_are_preserved(self):
        target = self.article("index.qmd", '''<!doctype html>
<p>正文</p>
<link data-note="href='wrong.css'" REL='alternate STYLESHEET' href='assets/guide.css?theme=dark&amp;label=%E4%B8%AD&amp;v=old&amp;v=older#reader'/>
''')
        self.version()
        text = target.read_text()
        href = StylesheetHTML(text).links[0]["href"]
        self.assertEqual(href, "assets/guide.css?theme=dark&label=%E4%B8%AD&v=" + self.digest() + "#reader")
        self.assertIn('data-note="href=\'wrong.css\'"', text)
        self.assertIn("theme=dark&amp;label=", text)
        self.assertNotIn("&amp;amp;", text)

    def test_versioning_is_idempotent_and_refreshes_when_stylesheet_changes(self):
        target = self.article("index.qmd", '<link rel=stylesheet href=assets/guide.css>')
        self.assertEqual(self.version(), 1)
        first = target.read_text()
        self.assertEqual(self.version(), 0)
        self.assertEqual(target.read_text(), first)
        self.css.write_text(".guide-profile-link { color: navy; }\n", encoding="utf-8")
        self.assertEqual(self.version(), 1)
        self.assertIn("?v=" + self.digest(), target.read_text())
        self.assertNotEqual(target.read_text(), first)

    def test_missing_stylesheet_or_missing_rendered_page_remains_compatible(self):
        target = self.article("index.qmd", '<link rel="stylesheet" href="assets/guide.css">')
        original = target.read_text()
        target.unlink()
        self.assertEqual(self.version(), 0)
        target.write_text(original, encoding="utf-8")
        self.css.unlink()
        self.assertEqual(self.version(), 0)
        self.assertEqual(target.read_text(), original)

    def test_main_versions_stylesheets_after_both_renders_before_exports(self):
        self.article("index.qmd", "fixture")
        self.article("en/index.qmd", "fixture")
        (self.book / "_quarto.yml").write_text("book: {}\n", encoding="utf-8")
        steps = []
        functions = {"prepare_english_config": "prepare", "validate_sources": "sources",
                     "version_stylesheets": "versions", "export_markdown": "markdown",
                     "export_redirects": "redirects", "validate_output": "output",
                     "validate_markdown": "markdown-check"}
        for name, label in functions.items():
            patcher = patch.object(build, name, side_effect=lambda *args, label=label: steps.append(label))
            patcher.start()
            self.addCleanup(patcher.stop)
        with patch.object(build, "run", side_effect=lambda *args, **kwargs: steps.append("render")), \
                patch.object(build, "giscus_settings"), patch("sys.argv", ["build.py", "--html-only"]), \
                patch.dict("os.environ", {"QUARTO": "test-quarto"}):
            build.main()
        self.assertEqual(steps, ["prepare", "sources", "render", "render", "versions", "markdown",
                                 "redirects", "output", "markdown-check"])


if __name__ == "__main__":
    unittest.main()
