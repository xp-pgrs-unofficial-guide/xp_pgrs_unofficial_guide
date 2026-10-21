"""Author breadcrumb groups are text in the published static HTML."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import build


class AuthorBreadcrumbTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.book = Path(temporary.name) / "book"
        self.output = self.book / "_book"
        self.output.mkdir(parents=True)
        (self.book / "index.qmd").write_text("---\ntitle: Home\n---\nHome.\n", encoding="utf-8")
        for name, value in (("BOOK", self.book), ("OUTPUT", self.output)):
            patcher = patch.object(build, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def page(self, relative, html, profile=True):
        source = self.book / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        if relative.startswith("en/"):
            (self.book / "en/index.qmd").write_text("---\ntitle: Home\n---\nHome.\n", encoding="utf-8")
        metadata = "guide-author-id: kai-wu\n" if profile else ""
        source.write_text("---\ntitle: Person\n" + metadata + "---\nBody.\n", encoding="utf-8")
        target = self.output / Path(relative).with_suffix(".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        return target

    def normalize(self):
        with redirect_stdout(io.StringIO()):
            return build.normalize_author_breadcrumbs()

    @staticmethod
    def breadcrumbs(parent, current):
        items = '<ol class="breadcrumb"><li class="breadcrumb-item">' + parent + \
                '</li><li class="breadcrumb-item">' + current + '</li></ol>'
        return ('<nav class="quarto-page-breadcrumbs" aria-label="breadcrumb">' + items + '</nav>\n'
                '<header><nav class="quarto-page-breadcrumbs quarto-title-breadcrumbs">' + items + '</nav></header>')

    def test_both_responsive_breadcrumbs_keep_the_author_link_in_each_language(self):
        cases = [
            ("authors/kai-wu.qmd", '<span>作者与贡献者</span>', '吴开'),
            ("en/authors/kai-wu.qmd", '<span>Authors&#32;and\n contributors</span>', 'Kai Wu'),
        ]
        expectations = []
        for source, inner, name in cases:
            parent = '<a HREF="../authors/kai-wu.html" data-label="parent > group">' + inner + '</a>'
            # The current author can have the same target as the misleading
            # parent link, so matching the href alone would remove too much.
            current = '<a href="../authors/kai-wu.html"><span class="chapter-title">' + name + '</span></a>'
            original = self.breadcrumbs(parent, current)
            target = self.page(source, original)
            expectations.append((target, original.replace(parent, inner), current))
        self.assertEqual(self.normalize(), 2)
        for target, expected, current in expectations:
            with self.subTest(page=target.name):
                self.assertEqual(target.read_text(), expected)
                self.assertEqual(target.read_text().count(current), 2)

    def test_sidebar_article_links_and_html_examples_are_preserved(self):
        parent = '<a href="../authors/kai-wu.html">作者与贡献者</a>'
        unchanged = '\n'.join([
            '<nav class="sidebar-navigation">' + parent + '</nav>',
            '<p>' + parent + '</p>',
            '<!-- <nav class="quarto-page-breadcrumbs">' + parent + '</nav> -->',
            '<script>const example = \'<nav class="quarto-page-breadcrumbs">' + parent + '</nav>\';</script>',
            '<nav class="quarto-page-breadcrumbs"><a href="../other.html">Other group</a></nav>',
        ])
        profile = self.page("authors/kai-wu.qmd", unchanged + '\n' + self.breadcrumbs(parent, '<a href="kai-wu.html">吴开</a>'))
        article_html = self.breadcrumbs(parent, '<a href="article.html">Article</a>')
        article = self.page("content/example.qmd", article_html, profile=False)
        self.assertEqual(self.normalize(), 1)
        self.assertTrue(profile.read_text().startswith(unchanged + '\n'))
        self.assertEqual(article.read_text(), article_html)

    def test_normalization_is_idempotent_and_skips_missing_or_plain_breadcrumbs(self):
        parent = '<a href="kai-wu.html">作者与贡献者</a>'
        target = self.page("authors/kai-wu.qmd", self.breadcrumbs(parent, '<a href="kai-wu.html">吴开</a>'))
        plain = self.page("authors/plain.qmd", '<nav class="quarto-page-breadcrumbs">作者与贡献者</nav>')
        missing = self.page("authors/missing.qmd", "unrendered")
        missing.unlink()
        self.assertEqual(self.normalize(), 1)
        first = target.read_text()
        self.assertEqual(self.normalize(), 0)
        self.assertEqual(target.read_text(), first)
        self.assertEqual(plain.read_text(), '<nav class="quarto-page-breadcrumbs">作者与贡献者</nav>')


if __name__ == "__main__":
    unittest.main()
