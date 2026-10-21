"""Author metadata must survive HTML, Markdown and PDF source generation."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FILTER = ROOT / "book/filters/author-pages.lua"
QUARTO = os.environ.get("QUARTO_BIN", "quarto")
PANDOC = os.environ.get("PANDOC_BIN")


class AuthorProfileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        (root / "index.qmd").write_text(
            '---\ntitle: Example article\ndiscussion-id: xp-guide-example\n---\n\n'
            '::: {.contribution authors="alice" contributors="bob"}\nArticle text.\n:::\n',
            encoding="utf-8",
        )
        self.meta = {
            "guide-source-root": str(root), "lang": "zh-CN",
            "book": {"chapters": ["index.qmd"]},
            "guide-authors": {"alice": "甲作者", "bob": "乙补充者", "editorial": "编辑组", "unknown": "归属待确认"},
            "guide-authors-en": {"alice": "Alice", "bob": "Bob", "editorial": "Editorial team", "unknown": "Unconfirmed"},
            "guide-author-profiles": {
                "alice": {
                    "type": "person", "project-roles": ["编辑"], "project-roles-en": ["Editor"],
                    "affiliation": "示例大学", "affiliation-en": "Example University",
                    "department": "科学系", "department-en": "Department of Science",
                    "research-interests": ["方向一", "方向二"], "research-interests-en": ["Topic one", "Topic two"],
                    "bio": "本人确认的简介。", "bio-en": "A biography confirmed by the author.",
                    "orcid": "0000-0002-1825-0097",
                    "google-scholar": "https://scholar.google.com/citations?user=example&hl=en",
                    "institutional-profile": "https://example.edu/people/alice",
                    "website": "https://alice.example/", "github": "https://github.com/example",
                },
                "bob": {"type": "person"}, "editorial": {"type": "team"}, "unknown": {"type": "placeholder"},
            },
        }

    def convert(self, output_format="html5", identifier="alice", index=False):
        placeholder = ('::: {.guide-author-index}\n:::\n' if index else
                       f'::: {{.guide-author-profile data-guide-author-id="{identifier}"}}\n:::\n')
        source = '---\n' + json.dumps(self.meta, ensure_ascii=False) + '\n---\n\nBefore.\n\n' + placeholder + '\nAfter.\n'
        result = subprocess.run(
            ([PANDOC] if PANDOC else [QUARTO, "pandoc"]) +
            ["--from=markdown", f"--to={output_format}", f"--lua-filter={FILTER}"],
            input=source, text=True, capture_output=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_chinese_profile_shows_confirmed_metadata_and_real_links_before_credits(self):
        html = self.convert()
        for text in ["作者资料", "项目角色", "编辑", "机构", "示例大学", "科学系", "方向一；方向二", "本人确认的简介。"]:
            self.assertIn(text, html)
        for address in ["https://orcid.org/0000-0002-1825-0097", "https://scholar.google.com/citations?user=example&amp;hl=en",
                        "https://example.edu/people/alice", "https://alice.example/", "https://github.com/example"]:
            self.assertIn('href="' + address + '"', html)
        self.assertIn("原作者", html)
        self.assertIn('href="../index.qmd"', html)
        self.assertLess(html.index("作者资料"), html.index("参与文章"))
        self.assertLess(html.index("Before."), html.index("作者资料"))
        self.assertLess(html.index("参与文章"), html.index("After."))
        self.assertNotIn("尚未提供学术资料", html)

    def test_english_profile_localizes_prose_without_changing_identifiers(self):
        self.meta["lang"] = "en"
        html = self.convert()
        normalized = " ".join(html.split())
        for text in ["Author profile", "Project roles", "Editor", "Affiliation", "Example University",
                     "Department of Science", "Topic one; Topic two", "A biography confirmed by the author.",
                     "Institutional profile", "Website", "Credited articles"]:
            self.assertIn(text, normalized)
        for text in ["示例大学", "科学系", "方向一", "本人确认的简介", "机构主页"]:
            self.assertNotIn(text, html)
        self.assertIn("https://orcid.org/0000-0002-1825-0097", html)
        self.assertIn('id="author-metadata-alice"', html)
        self.assertIn("substantive additions", " ".join(self.convert(identifier="bob").split()))

    def test_author_directory_summarizes_affiliation_and_links_with_article_counts(self):
        html = self.convert(index=True)
        self.assertIn('href="alice.qmd"', html)
        self.assertIn("1 篇文章 — 示例大学", html)
        self.assertIn('href="https://orcid.org/0000-0002-1825-0097"', html)
        self.assertIn("Google Scholar", " ".join(html.split()))
        self.assertIn('href="bob.qmd"', html)
        self.assertIn("历史归属", html)
        self.assertEqual(html.count('href="unknown.qmd"'), 1)
        self.assertNotIn("尚未提供学术资料", html)

    def test_missing_person_details_are_explicit_but_roles_do_not_imply_an_academic_profile(self):
        self.meta["guide-author-profiles"]["alice"] = {
            "type": "person", "project-roles": ["编辑"], "project-roles-en": ["Editor"]}
        html = self.convert()
        self.assertIn("项目角色", html)
        self.assertIn("尚未提供学术资料。", html)
        self.assertNotIn("orcid.org", html)
        self.assertNotIn("scholar.google", html)
        for identifier in ["editorial", "unknown"]:
            result = self.convert(identifier=identifier)
            self.assertNotIn("尚未提供学术资料", result)
            self.assertNotIn("作者资料", result)
            self.assertIn("参与文章", result)

    def test_markdown_and_latex_keep_native_metadata_and_their_credit_targets(self):
        markdown = self.convert("gfm")
        self.assertIn("https://orcid.org/0000-0002-1825-0097", markdown)
        self.assertIn("方向一；方向二", markdown)
        self.assertIn("../index.qmd", markdown)
        self.assertNotIn("guide-author-expanded", markdown)
        self.assertNotIn("data-guide-author-id", markdown)
        latex = self.convert("latex")
        self.assertIn("https://orcid.org/0000-0002-1825-0097", latex)
        self.assertIn("xp-guide-example", latex)
        self.assertIn("xp-guide-authors", latex)
        self.assertNotIn("../index.qmd", latex)
        self.assertNotIn("guide-author-expanded", latex)


if __name__ == "__main__":
    unittest.main()
