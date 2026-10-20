"""Verify grouped content discovery, exported links, and legacy URL redirects.

Uses temporary projects, real Pandoc conversions, and Node to execute the
generated redirect script. Run with python3 -m unittest discover -s tests/build.
"""

from contextlib import redirect_stdout
from html import escape
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urljoin

import yaml

from scripts import build


REAL_BOOK = build.BOOK
SITE = "https://example.test/guide/"


class RedirectHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.canonical = None
        self.scripts = []
        self.current_script = None

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == "a" and fields.get("href"):
            self.hrefs.append(fields["href"])
        if tag == "link" and fields.get("rel") == "canonical":
            self.canonical = fields["href"]
        if tag == "script" and not fields.get("src"):
            self.current_script = []

    def handle_data(self, data):
        if self.current_script is not None:
            self.current_script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current_script is not None:
            self.scripts.append("".join(self.current_script))
            self.current_script = None


class TemporaryBook(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.book = self.root / "book"
        self.output = self.book / "_book"
        self.output.mkdir(parents=True)
        self.articles = {
            "index.qmd": ("Home", "xp-guide-home"),
            "content/milestones/apr.qmd": ("Annual review", "xp-guide-apr"),
            "content/resources/funding.qmd": ("Funding", "xp-guide-funding"),
            "content/appendix/contributing.qmd": ("Contributing", "xp-guide-contributing"),
        }
        for relative in self.articles:
            self.write_source(relative)
        self.config = {
            "guide-repo": "https://github.com/example/guide",
            "guide-site": SITE,
            "book": {"chapters": list(self.articles), "site-url": SITE},
        }
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(self.config), encoding="utf-8")
        (self.book / "_authors.yml").write_text("guide-authors:\n  editorial: Editors\n", encoding="utf-8")
        shutil.copytree(REAL_BOOK / "filters", self.book / "filters")
        (self.book / "assets").mkdir()
        (self.book / "assets/figure.png").write_bytes(b"fixture asset")
        (self.output / "assets").mkdir()
        (self.output / "assets/figure.png").write_bytes(b"fixture asset")
        for name, value in (("ROOT", self.root), ("BOOK", self.book), ("OUTPUT", self.output)):
            patcher = patch.object(build, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {
            "GISCUS_REPO_ID": "", "GISCUS_CATEGORY_ID": "", "GISCUS_CATEGORY": "",
        })
        environment.start()
        self.addCleanup(environment.stop)

    def write_source(self, relative, body="CURRENT SOURCE TEXT"):
        title, identifier = self.articles[relative]
        target = self.book / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"---\ntitle: {title}\ndiscussion-id: {identifier}\n---\n\n"
            f"::: {{#{identifier}}}\n:::\n\n::: {{.contribution authors=\"editorial\"}}\n\n{body}\n\n:::\n",
            encoding="utf-8",
        )

    def write_redirects(self, aliases=None, text=None):
        if text is None:
            text = yaml.safe_dump({"schema_version": 1, "redirects": aliases or {}})
        (self.book / "redirects.yml").write_text(text, encoding="utf-8")

    def write_html(self):
        settings = build.giscus_settings(self.config)
        for relative, (_, identifier) in self.articles.items():
            target = self.output / Path(relative).with_suffix(".html")
            target.parent.mkdir(parents=True, exist_ok=True)
            text = f'<h1 id="{identifier}">Article</h1>'
            if settings:
                fields = {"type": "application/json", "class": "guide-giscus-config",
                          "data-src": "https://giscus.app/client.js", **settings, "data-term": identifier}
                attributes = " ".join(f'{key}="{escape(value, quote=True)}"' for key, value in fields.items())
                text += f"<script {attributes}></script>"
            target.write_text(text, encoding="utf-8")
        (self.output / "search.json").write_text(
            json.dumps([{"text": title} for title, _ in self.articles.values()]), encoding="utf-8")

    def pandoc_run(self, command, **options):
        self.assertEqual(str(command[1]), "pandoc")
        binary = os.environ.get("PANDOC_BIN")
        prefix = [binary] if binary else [os.environ.get("QUARTO_BIN", "quarto"), "pandoc"]
        return subprocess.run(prefix + [str(part) for part in command[2:]], check=True, cwd=self.root, **options)

    def quietly(self, function, *arguments, **options):
        with redirect_stdout(io.StringIO()):
            return function(*arguments, **options)


class ContentPathTests(TemporaryBook):
    def test_recursive_discovery_includes_every_article_and_no_generated_file(self):
        self.articles["content/resources/nested/extra.qmd"] = ("Deep article", "xp-guide-extra")
        self.write_source("content/resources/nested/extra.qmd")
        (self.output / "ignored.qmd").write_text("generated", encoding="utf-8")
        expected = {self.book / relative for relative in self.articles}
        actual = build.pages()
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))
        self.assertEqual(actual[0], self.book / "index.qmd")

    def test_real_markdown_export_resolves_cross_group_links_assets_and_index(self):
        self.write_source("index.qmd", "[Annual review](content/milestones/apr.qmd#xp-guide-apr)")
        self.write_source("content/milestones/apr.qmd", "\n\n".join([
            "[Funding](../resources/funding.qmd?view=1#xp-guide-funding)",
            "![Figure](../../assets/figure.png)",
            "[Markdown index](../../llms.txt)",
            "[Current section](#xp-guide-apr)",
            "[External](https://example.net/guide.qmd?mode=1#read)",
        ]))
        with patch.object(build, "run", self.pandoc_run):
            self.quietly(build.export_markdown, "test-quarto")
        article = self.output / "markdown/content/milestones/apr.md"
        text = article.read_text(encoding="utf-8")
        for target in ("../resources/funding.md?view=1#xp-guide-funding",
                       "../../../assets/figure.png", "../../../llms.txt", "#xp-guide-apr",
                       "https://example.net/guide.qmd?mode=1#read"):
            self.assertIn(target, text)
        self.assertIn("content/milestones/apr.md#xp-guide-apr", (self.output / "markdown/index.md").read_text())
        self.assertIn("markdown/content/milestones/apr.md", (self.output / "llms.txt").read_text())
        search = json.loads((self.output / "search.json").read_text())
        self.assertEqual({entry["href"] for entry in search},
                         {str(Path(relative).with_suffix(".html")) for relative in self.articles})
        with patch.object(build, "run", self.pandoc_run):
            self.quietly(build.validate_markdown, "test-quarto")

    def test_missing_redirect_manifest_is_optional(self):
        self.assertEqual(build.load_redirects(), {})

    def test_multiple_historical_addresses_may_target_the_same_article(self):
        aliases = {"content/old-apr.qmd": "content/milestones/apr.qmd",
                   "content/older-apr.qmd": "content/milestones/apr.qmd"}
        self.write_redirects(aliases)
        self.assertEqual(build.load_redirects(), aliases)

    def test_invalid_redirect_paths_targets_conflicts_and_chains_fail(self):
        invalid = [
            {"../outside.qmd": "content/milestones/apr.qmd"},
            {"/absolute.qmd": "content/milestones/apr.qmd"},
            {"https://example.net/old.qmd": "content/milestones/apr.qmd"},
            {"content/old.html": "content/milestones/apr.qmd"},
            {"index.qmd": "content/milestones/apr.qmd"},
            {"content/old.qmd": "content/missing.qmd"},
            {"content/old.qmd": "../outside.qmd"},
            {"content/old.qmd": "content/apr.html"},
            {"content/%2e%2e/old.qmd": "content/milestones/apr.qmd"},
            {"content/old.qmd?mode=1": "content/milestones/apr.qmd"},
            {"content/old.qmd#section": "content/milestones/apr.qmd"},
            {"content/old.qmd": "content/older.qmd", "content/older.qmd": "content/milestones/apr.qmd"},
        ]
        for aliases in invalid:
            with self.subTest(aliases=aliases):
                self.write_redirects(aliases)
                with self.assertRaises(ValueError):
                    build.load_redirects()

    def test_redirect_alias_cannot_escape_through_a_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.book / "escape").symlink_to(outside, target_is_directory=True)
        self.write_redirects({"escape/old.qmd": "content/milestones/apr.qmd"})
        with self.assertRaises(ValueError):
            build.load_redirects()

    def test_duplicate_alias_keys_and_invalid_schema_fail(self):
        invalid = [
            "schema_version: 1\nredirects:\n  content/old.qmd: content/milestones/apr.qmd\n  content/old.qmd: content/resources/funding.qmd\n",
            "schema_version: 2\nredirects: {}\n",
            "schema_version: 1\nredirects: []\n",
        ]
        for text in invalid:
            with self.subTest(text=text):
                self.write_redirects(text=text)
                with self.assertRaises(ValueError):
                    build.load_redirects()


class RedirectOutputTests(TemporaryBook):
    def setUp(self):
        super().setUp()
        self.write_redirects({"content/old-apr.qmd": "content/milestones/apr.qmd",
                              "legacy.qmd": "content/appendix/contributing.qmd"})

    def test_redirect_script_preserves_query_and_hash_and_has_a_fallback(self):
        self.quietly(build.export_redirects)
        text = (self.output / "content/old-apr.html").read_text(encoding="utf-8")
        parser = RedirectHTML()
        parser.feed(text)
        self.assertEqual(parser.canonical, SITE + "content/milestones/apr.html")
        self.assertIn("milestones/apr.html", parser.hrefs)
        self.assertEqual(len(parser.scripts), 1)
        node = os.environ.get("NODE_BIN", "node")
        program = """
const vm = require('node:vm');
const payload = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const page = new URL(payload.base);
let replacement;
const location = {href: page.href, search: page.search, hash: page.hash,
                  replace(value) { replacement = value; }};
vm.runInNewContext(payload.script, {URL, window: {location}, location});
if (typeof replacement !== 'string') throw Error('No redirect was performed');
process.stdout.write(new URL(replacement, page).href);
"""
        for suffix in ("", "?from=legacy&mode=a%20b#sec.IPAP"):
            with self.subTest(suffix=suffix):
                result = subprocess.run([node, "-e", program], input=json.dumps({
                    "script": parser.scripts[0], "base": SITE + "content/old-apr.html" + suffix,
                }), text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout, SITE + "content/milestones/apr.html" + suffix)
        markdown = (self.output / "markdown/content/old-apr.md").read_text(encoding="utf-8")
        self.assertIn("milestones/apr.md", markdown)
        self.assertNotIn("CURRENT SOURCE TEXT", markdown)
        root_alias = RedirectHTML()
        root_alias.feed((self.output / "legacy.html").read_text())
        self.assertEqual(root_alias.canonical, SITE + "content/appendix/contributing.html")
        self.assertEqual(urljoin(SITE + "legacy.html", root_alias.hrefs[0]), root_alias.canonical)
        self.assertIn("content/appendix/contributing.md", (self.output / "markdown/legacy.md").read_text())

    def test_redirects_do_not_need_giscus_but_authored_articles_do(self):
        with patch.dict(os.environ, {"GISCUS_REPO_ID": "repository-id", "GISCUS_CATEGORY_ID": "category-id"}):
            self.write_html()
            self.quietly(build.export_redirects)
            self.quietly(build.validate_output, html_only=True)
            (self.output / "content/milestones/apr.html").write_text("<h1>Article without comments</h1>")
            with self.assertRaisesRegex(ValueError, "Giscus"):
                self.quietly(build.validate_output, html_only=True)

    def test_redirects_reject_inert_and_executable_giscus_embeds(self):
        self.write_redirects({"content/old-apr.qmd": "content/milestones/apr.qmd"})
        self.write_html()
        self.quietly(build.export_redirects)
        redirect = self.output / "content/old-apr.html"
        original = redirect.read_text()
        for embed in ('<script type="application/json" class="guide-giscus-config" '
                      'data-src="https://giscus.app/client.js">{}</script>',
                      '<script src="https://giscus.app/client.js"></script>'):
            with self.subTest(embed=embed):
                redirect.write_text(original + embed)
                with self.assertRaisesRegex(ValueError, "兼容跳转不应包含 Giscus"):
                    self.quietly(build.validate_output, html_only=True)

    def test_redirect_targets_are_still_checked(self):
        self.write_html()
        self.quietly(build.export_redirects)
        (self.output / "content/milestones/apr.html").unlink()
        with self.assertRaises(ValueError):
            self.quietly(build.validate_output, html_only=True)

    def test_old_article_fragments_are_checked_on_the_current_article(self):
        self.write_html()
        self.quietly(build.export_redirects)
        home = self.output / "index.html"
        home.write_text('<a href="content/old-apr.html#xp-guide-apr">Legacy article section</a>')
        self.quietly(build.validate_output, html_only=True)
        home.write_text('<a href="content/old-apr.html#nonexistent">Broken legacy section</a>')
        with self.assertRaisesRegex(ValueError, "锚点不存在"):
            self.quietly(build.validate_output, html_only=True)

    def test_export_cannot_overwrite_an_existing_output_file(self):
        old = self.output / "content/old-apr.html"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("Existing authored output", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.quietly(build.export_redirects)
        self.assertEqual(old.read_text(), "Existing authored output")


if __name__ == "__main__":
    unittest.main()
