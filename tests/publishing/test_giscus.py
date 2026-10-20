"""Check that generated article comments use the configured, independent discussions.

Run with python3 -m unittest discover -s tests/publishing.
"""

from contextlib import redirect_stdout
from html import escape
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import build


GISCUS_ATTRIBUTES = {
    "data-repo": "example/guide",
    "data-repo-id": "repository-id",
    "data-category": "文章评论",
    "data-category-id": "category-id",
    "data-mapping": "specific",
    "data-strict": "1",
    "data-lang": "zh-CN",
}


class GiscusOutputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.book = (Path(temporary.name) / "book").resolve()
        self.output = self.book / "_book"
        (self.book / "content").mkdir(parents=True)
        (self.output / "content").mkdir(parents=True)
        self.config = {"guide-repo": "https://github.com/example/guide"}
        (self.book / "_quarto.yml").write_text(
            "guide-repo: https://github.com/example/guide\n", encoding="utf-8")
        self.sources = [self.book / "index.qmd", self.book / "content/apr.qmd"]
        for source, term in zip(self.sources, ("xp-guide-home", "xp-guide-apr")):
            source.write_text(f"---\ntitle: Article\ndiscussion-id: {term}\n---\nBody.\n", encoding="utf-8")
        (self.output / "search.json").write_text(
            json.dumps([{"text": "Home"}, {"text": "APR"}]), encoding="utf-8")
        for name, value in (("BOOK", self.book), ("OUTPUT", self.output), ("pages", lambda: self.sources)):
            patcher = patch.object(build, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {
            "GISCUS_REPO_ID": "repository-id",
            "GISCUS_CATEGORY_ID": "category-id",
            "GISCUS_CATEGORY": "文章评论",
        }, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.write_article("index.html", "xp-guide-home")
        self.write_article("content/apr.html", "xp-guide-apr")

    def write_article(self, relative, term, **overrides):
        fields = {"src": "https://giscus.app/client.js", **GISCUS_ATTRIBUTES, "data-term": term}
        fields.update(overrides)
        attributes = " ".join(f'{key}="{escape(value, quote=True)}"' for key, value in fields.items())
        (self.output / relative).write_text(f"<script {attributes}></script>", encoding="utf-8")

    def validate(self):
        with redirect_stdout(io.StringIO()):
            build.validate_output(html_only=True)

    def test_each_article_accepts_its_own_discussion(self):
        self.validate()

    def test_reusing_another_articles_term_fails(self):
        self.write_article("content/apr.html", "xp-guide-home")
        with self.assertRaisesRegex(ValueError, "content/apr.html 的 Giscus data-term"):
            self.validate()

    def test_wrong_service_or_matching_attributes_fail(self):
        for field in GISCUS_ATTRIBUTES:
            with self.subTest(field=field):
                self.write_article("content/apr.html", "xp-guide-apr", **{field: "incorrect"})
                with self.assertRaisesRegex(ValueError, field):
                    self.validate()

    def test_missing_or_duplicate_comment_embed_fails(self):
        article = self.output / "content/apr.html"
        valid = article.read_text(encoding="utf-8")
        for text in ("<p>No comments</p>", valid + valid):
            article.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "必须包含一个独立 Giscus 讨论区"):
                self.validate()

    def test_partial_configuration_fails_before_rendering(self):
        for environment in ({"GISCUS_REPO_ID": "repository-id"},
                            {"GISCUS_CATEGORY_ID": "category-id"},
                            {"GISCUS_CATEGORY": "文章评论"}):
            with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, "必须同时设置"):
                    build.validate_sources("unused-quarto")

    def test_absent_configuration_keeps_comments_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(build.giscus_settings(self.config))
            for relative in ("index.html", "content/apr.html"):
                (self.output / relative).write_text("<p>Discussion link</p>", encoding="utf-8")
            self.validate()


if __name__ == "__main__":
    unittest.main()
