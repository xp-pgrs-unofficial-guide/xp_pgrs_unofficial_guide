"""Exercise actual article contribution links through the production Lua filter.

Run with PANDOC_BIN=/path/to/pandoc python3 -m unittest discover -s tests/publishing.
QUARTO_BIN=/path/to/quarto is also supported; the default is quarto pandoc.
"""

from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import unittest
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
FILTER = ROOT / "book/filters/publishing.lua"
WRAPPER = ROOT / "tests/publishing/quarto_stub.lua"
REPO = "https://github.com/example/guide"
SITE = "https://example.github.io/guide/"


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.scripts = []
        self.current = None
        self.text = []

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == "script" and fields.get("src"):
            self.scripts.append(fields["src"])
        if tag == "a":
            self.current = {**fields, "label": ""}

    def handle_data(self, data):
        self.text.append(data)
        if self.current is not None:
            self.current["label"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.anchors.append(self.current)
            self.current = None


def convert(input_file="content/apr.qmd", title="APR", branch="main",
            discussion="xp-guide-apr", output_format="html5", body="Article text.",
            lang="zh-CN", source_prefix="", site=SITE, site_root=SITE, translation_status=None):
    metadata = [
        "---", f"title: {json.dumps(title, ensure_ascii=False)}",
        f"discussion-id: {discussion}", f"guide-repo: {REPO}", f"guide-site: {site}",
        f"lang: {json.dumps(lang)}", f"guide-source-prefix: {json.dumps(source_prefix)}",
    ]
    if site_root is not None:
        metadata.append(f"guide-site-root: {site_root}")
    if translation_status is not None:
        metadata.append(f"translation-status: {translation_status}")
    if branch is not None:
        metadata.extend(["book:", f"  repo-branch: {json.dumps(branch)}"])
    metadata.extend(["---", "", body])
    environment = os.environ.copy()
    environment["GUIDE_TEST_INPUT"] = input_file
    environment["GUIDE_TEST_PUBLISHING_FILTER"] = str(FILTER)
    for variable in ("GISCUS_REPO_ID", "GISCUS_CATEGORY_ID", "GISCUS_CATEGORY"):
        environment.pop(variable, None)
    pandoc = environment.get("PANDOC_BIN")
    command = [pandoc] if pandoc else [environment.get("QUARTO_BIN", "quarto"), "pandoc"]
    return subprocess.run(
        command + ["--from=markdown", f"--to={output_format}", f"--lua-filter={WRAPPER}"],
        input="\n".join(metadata), text=True, capture_output=True, cwd=ROOT, env=environment,
    )


class ContributionLinkTests(unittest.TestCase):
    def parse(self, **options):
        result = convert(**options)
        self.assertEqual(result.returncode, 0, result.stderr)
        parser = Anchors()
        parser.feed(result.stdout)
        issue = [link for link in parser.anchors if urlsplit(link.get("href", "")).path.endswith("/issues/new")]
        edits = [link for link in parser.anchors if "/edit/" in link.get("href", "")]
        self.assertEqual(len(issue), 1)
        self.assertEqual(len(edits), 1)
        return parser, issue[0], edits[0]

    def test_home_and_nested_articles_prefill_their_own_context(self):
        contexts = [
            ("index.qmd", "index.qmd", "欢迎阅读", "xp-guide-home"),
            ("content/apr.qmd", "content/apr.qmd", "APR", "xp-guide-apr"),
            (str(ROOT / "book/content/apr.qmd"), "content/apr.qmd", "APR", "xp-guide-apr"),
            ("content/milestones/apr.qmd", "content/milestones/apr.qmd", "APR", "xp-guide-apr"),
            (str(ROOT / "book/content/milestones/apr.qmd"), "content/milestones/apr.qmd", "APR", "xp-guide-apr"),
        ]
        for input_file, source, title, discussion in contexts:
            with self.subTest(input_file=input_file):
                _, issue, edit = self.parse(input_file=input_file, title=title, discussion=discussion)
                issue_url = urlsplit(issue["href"])
                self.assertEqual(issue_url._replace(query="", fragment="").geturl(), REPO + "/issues/new")
                query = parse_qs(issue_url.query)
                self.assertEqual(set(query), {"title", "body"})
                self.assertIn(title, query["title"][0])
                body = unquote(query["body"][0])
                for context in (title, SITE + source.replace(".qmd", ".html"),
                                "book/" + source, "源分支：main", discussion,
                                "内容", "署名", "来源"):
                    self.assertIn(context, body)
                self.assertNotIn(str(ROOT), body)
                self.assertEqual(edit["href"], REPO + "/edit/main/book/" + source)

    def test_unicode_and_reserved_characters_cannot_split_query_or_path(self):
        source = 'content/复核 & "说明"?.qmd'
        title = '复核 & APR? "说明"'
        parser, issue, edit = self.parse(input_file=source, title=title)
        query = parse_qs(urlsplit(issue["href"]).query)
        self.assertEqual(set(query), {"title", "body"})
        self.assertEqual(len(query["title"]), 1)
        self.assertEqual(len(query["body"]), 1)
        self.assertIn("复核 & APR?", query["title"][0])
        self.assertIn(source, query["body"][0])
        self.assertIn(SITE + source.replace(".qmd", ".html"), unquote(query["body"][0]))
        self.assertEqual(unquote(urlsplit(edit["href"]).path), "/example/guide/edit/main/book/" + source)
        self.assertEqual(urlsplit(edit["href"]).query, "")
        self.assertEqual(urlsplit(edit["href"]).fragment, "")
        self.assertEqual(edit["label"], "提出修改（PR）")
        self.assertIn("fork", "".join(parser.text).lower())

    def test_source_branch_is_configurable_for_publication(self):
        _, issue, edit = self.parse(branch="codex/contribution-test")
        self.assertEqual(edit["href"], REPO + "/edit/codex/contribution-test/book/content/apr.qmd")
        body = parse_qs(urlsplit(issue["href"]).query)["body"][0]
        self.assertIn("codex/contribution-test", body)
        self.assertNotIn("源分支：main", body)

    def test_missing_source_branch_fails_instead_of_linking_to_another_branch(self):
        result = convert(branch=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repo-branch", result.stderr)

    def test_both_pdf_downloads_use_the_shared_site_root_in_either_language(self):
        for lang, prefix in [("zh-CN", ""), ("en", "en/")]:
            for source in ("index.qmd", "content/milestones/apr.qmd", "authors/kai-wu.qmd"):
                with self.subTest(lang=lang, source=source):
                    parser, _, _ = self.parse(input_file=source, lang=lang,
                                              site=SITE + prefix, source_prefix=prefix)
                    downloads = [link for link in parser.anchors
                                 if "guide-pdf-download" in link.get("class", "").split()]
                    self.assertEqual([(link["hreflang"], link["href"]) for link in downloads], [
                        ("zh-CN", SITE + "xp-pgrs-unofficial-guide.pdf"),
                        ("en", SITE + "en/xp-pgrs-unofficial-guide.pdf"),
                    ])
                    self.assertTrue(all("no-external" in link["class"].split() for link in downloads))
                    self.assertEqual(downloads[0]["label"], "Chinese PDF" if lang == "en" else "中文版 PDF")
                    self.assertEqual(downloads[1]["label"], "English PDF")
                    self.assertEqual(len([link for link in parser.anchors
                                          if link["href"] == REPO + "/releases/latest"]), 1)

    def test_footer_links_resolve_from_each_article_depth(self):
        contexts = [
            ("index.qmd", "markdown/index.md", "assets/guide.js"),
            ("content/apr.qmd", "../markdown/content/apr.md", "../assets/guide.js"),
            ("content/milestones/apr.qmd", "../../markdown/content/milestones/apr.md", "../../assets/guide.js"),
        ]
        for source, markdown, script in contexts:
            with self.subTest(source=source):
                parser, _, _ = self.parse(input_file=source)
                links = [link for link in parser.anchors if link["label"] == "纯 Markdown"]
                self.assertEqual([link["href"] for link in links], [markdown])
                self.assertEqual(parser.scripts, [script])

    def test_pdf_attachments_and_llms_resolve_from_deep_articles(self):
        body = "\n\n".join([
            "[Attachment](../../assets/imported/handout.pdf)",
            "[Markdown index](../../llms.txt)",
            "[External](https://example.net/other.pdf)",
        ])
        result = convert(input_file="content/milestones/apr.qmd", output_format="latex", body=body)
        self.assertEqual(result.returncode, 0, result.stderr)
        for url in (SITE + "assets/imported/handout.pdf", SITE + "llms.txt", "https://example.net/other.pdf"):
            self.assertIn("\\href{" + url + "}", result.stdout)
        self.assertNotIn("../", result.stdout)
        self.assertNotIn("guide-participate", result.stdout)


    def test_english_articles_prefill_the_translation_source_and_shared_discussion(self):
        contexts = [
            ("index.qmd", "index.qmd", "Welcome", "xp-guide-home"),
            ("content/milestones/apr.qmd", "content/milestones/apr.qmd", "APR", "xp-guide-apr"),
            (str(ROOT / "book/en/content/milestones/apr.qmd"), "content/milestones/apr.qmd", "APR", "xp-guide-apr"),
        ]
        for input_file, source, title, discussion in contexts:
            with self.subTest(input_file=input_file):
                _, issue, edit = self.parse(input_file=input_file, title=title, discussion=discussion,
                                           lang="en", source_prefix="en/", site=SITE + "en/")
                query = parse_qs(urlsplit(issue["href"]).query)
                self.assertEqual(set(query), {"title", "body"})
                self.assertEqual(query["title"][0], "[Addition / correction] " + title)
                body = query["body"][0]
                for context in ("Title: " + title, "Source: book/en/" + source,
                                "URL: " + SITE + "en/" + source.replace(".qmd", ".html"),
                                "Discussion ID: " + discussion, "Branch: main",
                                "Public name or pseudonym", "Source and date checked"):
                    self.assertIn(context, body)
                self.assertNotIn(str(ROOT), body)
                self.assertEqual(edit["href"], REPO + "/edit/main/book/en/" + source)
                self.assertEqual(edit["label"], "Propose an edit (PR)")

    def test_language_switches_point_to_the_same_article_in_the_other_language(self):
        contexts = [
            ("index.qmd", "zh-CN", SITE, "", SITE + "en/index.html", "en"),
            ("content/milestones/apr.qmd", "zh-CN", SITE, "", SITE + "en/content/milestones/apr.html", "en"),
            ("content/milestones/apr.qmd", "en", SITE + "en/", "en/", SITE + "content/milestones/apr.html", "zh-CN"),
        ]
        for source, lang, site, prefix, target, alternate_lang in contexts:
            with self.subTest(source=source, lang=lang):
                parser, _, _ = self.parse(input_file=source, lang=lang, site=site, source_prefix=prefix)
                switches = [link for link in parser.anchors if "guide-language-switch" in link.get("class", "").split()]
                self.assertEqual(len(switches), 1)
                self.assertEqual(switches[0]["href"], target)
                self.assertEqual(switches[0]["hreflang"], alternate_lang)
                self.assertEqual(switches[0]["target"], "_self")
                # Quarto treats the Chinese root as external to its English subsite.
                # Its browser script otherwise replaces even explicit _self targets.
                self.assertIn("no-external", switches[0].get("class", "").split())

    def test_english_footer_links_keep_markdown_local_and_javascript_shared(self):
        contexts = [
            ("index.qmd", "markdown/index.md", "../assets/guide.js"),
            ("content/milestones/apr.qmd", "../../markdown/content/milestones/apr.md", "../../../assets/guide.js"),
            ("authors/kai-wu.qmd", "../markdown/authors/kai-wu.md", "../../assets/guide.js"),
        ]
        for source, markdown, script in contexts:
            with self.subTest(source=source):
                parser, _, _ = self.parse(input_file=source, lang="en", site=SITE + "en/", source_prefix="en/")
                links = [link for link in parser.anchors if link["label"] == "Plain Markdown"]
                self.assertEqual([link["href"] for link in links], [markdown])
                self.assertEqual(parser.scripts, [script])

    def test_english_pdf_uses_shared_attachments_and_its_own_markdown_index(self):
        body = "\n\n".join([
            "[Attachment](../../../assets/imported/handout.pdf)",
            "[Markdown index](../../llms.txt)",
            "[External](https://example.net/other.pdf)",
        ])
        result = convert(input_file="content/milestones/apr.qmd", lang="en", site=SITE + "en/",
                         source_prefix="en/", output_format="latex", body=body)
        self.assertEqual(result.returncode, 0, result.stderr)
        for url in (SITE + "assets/imported/handout.pdf", SITE + "en/llms.txt", "https://example.net/other.pdf"):
            self.assertIn("\\href{" + url + "}", result.stdout)
        self.assertNotIn(SITE + "en/assets/", result.stdout)
        self.assertNotIn("../", result.stdout)

    def test_translation_draft_notice_links_to_the_current_chinese_source(self):
        parser, _, _ = self.parse(input_file="content/milestones/apr.qmd", lang="en", site=SITE + "en/",
                                  source_prefix="en/", translation_status="draft")
        self.assertIn("awaiting human review", "".join(parser.text))
        source = [link for link in parser.anchors if link["label"] == "Read the Chinese source"]
        self.assertEqual(len(source), 1)
        self.assertEqual(source[0]["href"], SITE + "content/milestones/apr.html")
        self.assertEqual(source[0]["target"], "_self")
        self.assertIn("no-external", source[0].get("class", "").split())


if __name__ == "__main__":
    unittest.main()
