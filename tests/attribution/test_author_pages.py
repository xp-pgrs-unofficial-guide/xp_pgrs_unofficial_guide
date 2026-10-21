"""Author metadata must survive HTML, Markdown and PDF source generation."""

import base64
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FILTER = ROOT / "book/filters/author-pages.lua"
QUARTO = os.environ.get("QUARTO_BIN", "quarto")
PANDOC = os.environ.get("PANDOC_BIN")


class ProfileMarkup(HTMLParser):
    """Inspect link semantics independently of Pandoc's attribute ordering."""

    def __init__(self, source):
        super().__init__()
        self.nodes = []
        self.stack = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        node = {"tag": tag, "attributes": dict(attributes), "children": []}
        self.nodes.append(node)
        if self.stack:
            self.stack[-1]["children"].append(node)
        if tag not in {"img", "br", "hr", "meta", "link", "input"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, text):
        if self.stack:
            self.stack[-1]["children"].append(text)

    def elements(self, tag=None, class_name=None, root=None):
        def descendants(node):
            yield node
            for child in node["children"]:
                if isinstance(child, dict):
                    yield from descendants(child)
        candidates = descendants(root) if root else self.nodes
        return [node for node in candidates if (tag is None or node["tag"] == tag) and
                (class_name is None or class_name in node["attributes"].get("class", "").split())]

    @staticmethod
    def text(node):
        return "".join(ProfileMarkup.text(child) if isinstance(child, dict) else child
                       for child in node["children"])


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
                    "email": "alice@example.edu",
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
        for marker in ["guide-profile-link", "<svg", "data:image", "aria-label", "guide-profile-tooltip"]:
            self.assertNotIn(marker, markdown)
        latex = self.convert("latex")
        self.assertIn("https://orcid.org/0000-0002-1825-0097", latex)
        self.assertIn("xp-guide-example", latex)
        self.assertIn("xp-guide-authors", latex)
        self.assertNotIn("../index.qmd", latex)
        self.assertNotIn("guide-author-expanded", latex)
        for marker in ["guide-profile-link", "<svg", "data:image", "aria-label", "guide-profile-tooltip"]:
            self.assertNotIn(marker, latex)

    def test_email_is_a_localized_contact_link_in_profiles_directories_and_exports(self):
        for index in [False, True]:
            parsed = ProfileMarkup(self.convert(index=index))
            email = next(node for node in parsed.elements("a", "guide-profile-link")
                         if node["attributes"]["data-profile-kind"] == "email")
            self.assertEqual(email["attributes"]["href"], "mailto:alice@example.edu")
            self.assertEqual(email["attributes"]["aria-label"], "甲作者 — 邮箱：alice@example.edu")
        for output_format in ["gfm", "latex"]:
            output = self.convert(output_format)
            self.assertIn("mailto:alice@example.edu", output)
            self.assertIn("alice@example.edu", output)
        self.meta["lang"] = "en"
        parsed = ProfileMarkup(self.convert())
        email = next(node for node in parsed.elements("a", "guide-profile-link")
                     if node["attributes"]["data-profile-kind"] == "email")
        self.assertEqual(email["attributes"]["aria-label"], "Alice — Email: alice@example.edu")
        self.meta["guide-author-profiles"]["alice"] = {"type": "person", "email": "alice@example.edu"}
        contact_only = " ".join(self.convert().split())
        self.assertIn("Academic profile details have not been provided yet.", contact_only)
        self.assertIn("mailto:alice@example.edu", contact_only)

    def test_html_profile_and_directory_use_accessible_local_icons_with_print_fallbacks(self):
        expected = {"orcid", "google-scholar", "institution", "website", "github", "email"}
        for index in [False, True]:
            parsed = ProfileMarkup(self.convert(index=index))
            links = parsed.elements("a", "guide-profile-link")
            self.assertEqual({node["attributes"]["data-profile-kind"] for node in links}, expected)
            group_class = "guide-profile-links-compact" if index else "guide-profile-links-profile"
            self.assertEqual(len(parsed.elements("span", group_class)), 1)
            for link in links:
                attributes = link["attributes"]
                self.assertTrue(attributes["aria-label"].startswith("甲作者 — "))
                self.assertEqual(attributes["title"], attributes["aria-label"])
                self.assertFalse("".join(child for child in link["children"] if isinstance(child, str)).strip(),
                                 "icon links must not have an always-visible text label")
                for class_name in ["guide-profile-icon", "guide-profile-tooltip", "guide-profile-print-label"]:
                    decorations = parsed.elements("span", class_name, root=link)
                    self.assertEqual(len(decorations), 1)
                    self.assertEqual(decorations[0]["attributes"]["aria-hidden"], "true")
                for svg in parsed.elements("svg", root=link):
                    self.assertEqual(svg["attributes"]["aria-hidden"], "true")
                    self.assertEqual(svg["attributes"]["focusable"], "false")
            github = next(node for node in links if node["attributes"]["data-profile-kind"] == "github")
            self.assertEqual(len(parsed.elements("svg", "guide-profile-icon-light", root=github)), 1)
            self.assertEqual(len(parsed.elements("svg", "guide-profile-icon-dark", root=github)), 1)
            scholar = next(node for node in links if node["attributes"]["data-profile-kind"] == "google-scholar")
            image = parsed.elements("img", root=scholar)[0]["attributes"]
            self.assertEqual(image["alt"], "")
            self.assertEqual(image["aria-hidden"], "true")
            self.assertTrue(image["src"].startswith("data:image/png;base64,"))
            decoded = base64.b64decode(image["src"].split(",", 1)[1], validate=True)
            self.assertEqual(decoded, (ROOT / "book/assets/icons/google-scholar.png").read_bytes())

    def test_repeated_official_svg_icons_keep_unique_clipping_ids(self):
        self.meta["guide-author-profiles"]["bob"]["github"] = "https://github.com/another-example"
        self.meta["guide-author-profiles"]["bob"]["orcid"] = "0000-0002-1694-233X"
        source = self.convert(index=True)
        parsed = ProfileMarkup(source)
        identifiers = [node["attributes"]["id"] for node in parsed.nodes if "id" in node["attributes"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        references = [match for node in parsed.nodes for attribute in node["attributes"].values()
                      for match in re.findall(r"url\(#([^)]+)\)", attribute or "")]
        self.assertTrue(references, "official GitHub assets include clipping paths")
        self.assertTrue(set(references).issubset(identifiers))
        self.assertNotRegex(source, r"\.st[01]\s*\{", "ORCID stylesheet classes must stay inside their own icon")
        scoped_classes = [name for node in parsed.nodes for name in node["attributes"].get("class", "").split()
                          if re.fullmatch(r"guide-profile-icon-\d+-st[01]", name)]
        self.assertTrue(scoped_classes)
        self.assertGreater(len(set(scoped_classes)), 2, "each ORCID copy must have its own style classes")


if __name__ == "__main__":
    unittest.main()
