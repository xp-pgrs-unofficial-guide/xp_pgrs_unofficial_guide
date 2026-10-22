"""Exercise actual article contribution links through the production Lua filter.

Run with PANDOC_BIN=/path/to/pandoc python3 -m unittest discover -s tests/publishing.
QUARTO_BIN=/path/to/quarto is also supported; the default is quarto pandoc.
"""

from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.parse import parse_qs, unquote, urljoin, urlsplit


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
        self.giscus_configs = []
        self.current = None
        self.text = []
        self.regions = []
        self.region_stack = []
        self.region_errors = []
        self.headings = []
        self.ids = []

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if fields.get("id"):
            self.ids.append(fields["id"])
        if tag in {"h2", "h3"}:
            self.headings.append((tag, fields, [name for _, names in self.region_stack for name in names]))
        if tag == "script" and fields.get("src"):
            self.scripts.append(fields["src"])
        if tag == "script" and "guide-giscus-config" in fields.get("class", "").split():
            self.giscus_configs.append(fields)
        if tag == "a":
            self.current = {**fields, "label": ""}
        if tag in {"section", "footer"}:
            classes = fields.get("class", "").split()
            ancestors = [name for _, names in self.region_stack for name in names]
            self.regions.append((tag, classes, ancestors))
            self.region_stack.append((tag, classes))

    def handle_data(self, data):
        self.text.append(data)
        if self.current is not None:
            self.current["label"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.anchors.append(self.current)
            self.current = None
        if tag in {"section", "footer"}:
            if not self.region_stack or self.region_stack[-1][0] != tag:
                self.region_errors.append(tag)
            else:
                self.region_stack.pop()


def convert(input_file="content/apr.qmd", title="APR", branch="main",
            discussion="xp-guide-apr", output_format="html5", body="Article text.",
            lang="zh-CN", source_prefix="", site=SITE, site_root=SITE, translation_status=None,
            cwd=ROOT, giscus=None):
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
    environment.update(giscus or {})
    pandoc = environment.get("PANDOC_BIN")
    command = [pandoc] if pandoc else [environment.get("QUARTO_BIN", "quarto"), "pandoc"]
    return subprocess.run(
        command + ["--from=markdown", f"--to={output_format}", f"--lua-filter={WRAPPER}"],
        input="\n".join(metadata), text=True, capture_output=True, cwd=cwd, env=environment,
    )


class ContributionLinkTests(unittest.TestCase):
    def versioned_script(self, path):
        digest = hashlib.sha1((ROOT / "book/assets/guide.js").read_bytes()).hexdigest()
        return path + "?v=" + digest

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

    def test_only_home_pages_offer_both_pdf_downloads_and_the_release_archive(self):
        for lang, prefix in [("zh-CN", ""), ("en", "en/")]:
            contexts = [
                ("index.qmd", True), (str(ROOT / "book" / prefix / "index.qmd"), True),
                ("content/milestones/apr.qmd", False), ("authors/kai-wu.qmd", False),
                ("authors/index.qmd", False),
            ]
            for source, home in contexts:
                with self.subTest(lang=lang, source=source):
                    parser, _, _ = self.parse(input_file=source, lang=lang,
                                              site=SITE + prefix, source_prefix=prefix)
                    downloads = [link for link in parser.anchors
                                 if "guide-pdf-download" in link.get("class", "").split()]
                    releases = [link for link in parser.anchors
                                if link["href"] == REPO + "/releases/latest"]
                    if not home:
                        self.assertEqual(downloads, [])
                        self.assertEqual(releases, [])
                        self.assertFalse(any("guide-downloads" in classes
                                             for _, classes, _ in parser.regions))
                        continue
                    self.assertEqual([(link["hreflang"], link["href"]) for link in downloads], [
                        ("zh-CN", SITE + "xp-pgrs-unofficial-guide.pdf"),
                        ("en", SITE + "en/xp-pgrs-unofficial-guide.pdf"),
                    ])
                    self.assertTrue(all("no-external" in link["class"].split() for link in downloads))
                    self.assertEqual(downloads[0]["label"], "Chinese PDF" if lang == "en" else "中文版 PDF")
                    self.assertEqual(downloads[1]["label"], "English PDF")
                    self.assertEqual(len(releases), 1)

    def test_participation_and_discussion_form_a_separate_closed_region_after_the_body(self):
        for lang in ("zh-CN", "en"):
            for source in ("index.qmd", "content/life-tools/liverpool-visit.qmd", "authors/index.qmd"):
                with self.subTest(lang=lang, source=source):
                    result = convert(input_file=source, lang=lang)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    parser = Anchors()
                    parser.feed(result.stdout)
                    self.assertEqual(parser.region_errors, [])
                    self.assertEqual(parser.region_stack, [])
                    afterword = [region for region in parser.regions if "guide-afterword" in region[1]]
                    self.assertEqual(afterword, [("footer", ["guide-afterword"], [])])
                    for name in ("guide-participate", "guide-discussion"):
                        self.assertEqual([ancestors for _, classes, ancestors in parser.regions
                                          if name in classes], [["guide-afterword"]])
                    for _, classes, ancestors in parser.regions:
                        if "guide-downloads" in classes:
                            self.assertEqual(ancestors, [])
                    label = "End of article · Contribute and discuss" if lang == "en" else "正文结束 · 参与与讨论"
                    self.assertIn(label, "".join(parser.text))
                    self.assertLess(result.stdout.index("Article text."), result.stdout.index('<footer class="guide-afterword"'))
                    if source == "index.qmd":
                        self.assertLess(result.stdout.index('class="guide-downloads"'),
                                        result.stdout.index('<footer class="guide-afterword"'))

    def test_footer_headings_own_their_anchors_after_an_article_subsection(self):
        body = '## Everyday life {#everyday-life}\n\n### Other libraries {#other-libraries}\n\nArticle text.'
        for lang, expected_ids in [("zh-CN", ["一起完善这一页", "讨论"]),
                                   ("en", ["help-improve-this-page", "discussion"])]:
            with self.subTest(lang=lang):
                parser, _, _ = self.parse(input_file="content/life-tools/liverpool-visit.qmd",
                                          lang=lang, body=body)
                footer = [fields for _, fields, ancestors in parser.headings if "guide-afterword" in ancestors]
                self.assertEqual([heading["id"] for heading in footer], expected_ids)
                self.assertEqual([heading["data-anchor-id"] for heading in footer], expected_ids)
                self.assertTrue(all("unlisted" in heading["class"].split() for heading in footer))
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                article = [fields for _, fields, ancestors in parser.headings if "guide-afterword" not in ancestors]
                self.assertEqual([heading["id"] for heading in article], ["everyday-life", "other-libraries"])
                self.assertEqual([heading["data-anchor-id"] for heading in article], ["everyday-life", "other-libraries"])

        for output_format in ("gfm", "latex"):
            result = convert(body=body, output_format=output_format)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("data-anchor-id", result.stdout)

    def test_publication_controls_are_absent_from_pdf_and_plain_markdown(self):
        for lang in ("zh-CN", "en"):
            for output_format in ("latex", "gfm"):
                for source in ("index.qmd", "content/life-tools/liverpool-visit.qmd"):
                    with self.subTest(lang=lang, output_format=output_format, source=source):
                        result = convert(input_file=source, lang=lang, output_format=output_format)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn("Article text.", result.stdout)
                        for marker in ("guide-downloads", "guide-afterword", "guide-participate", "guide-discussion"):
                            self.assertNotIn(marker, result.stdout)

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
                self.assertEqual(parser.scripts, [self.versioned_script(script)])

    def test_script_hash_resolves_from_the_filter_location_in_an_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            parser, _, _ = self.parse(input_file="content/milestones/apr.qmd", cwd=directory)
        self.assertEqual(parser.scripts, [self.versioned_script("../../assets/guide.js")])

    def test_giscus_configuration_waits_for_the_page_theme_script_in_both_languages(self):
        for lang in ("zh-CN", "en"):
            with self.subTest(lang=lang):
                parser, _, _ = self.parse(lang=lang, giscus={
                    "GISCUS_REPO_ID": "repository-id", "GISCUS_CATEGORY_ID": "category-id",
                })
                self.assertEqual(len(parser.giscus_configs), 1)
                self.assertEqual(parser.giscus_configs[0], {
                    "type": "application/json", "class": "guide-giscus-config",
                    "data-src": "https://giscus.app/client.js", "data-repo": "example/guide",
                    "data-repo-id": "repository-id", "data-category": "文章评论",
                    "data-category-id": "category-id", "data-mapping": "specific",
                    "data-term": "xp-guide-apr", "data-strict": "1", "data-reactions-enabled": "1",
                    "data-emit-metadata": "0", "data-input-position": "top",
                    "data-theme": "preferred_color_scheme", "data-lang": lang, "data-loading": "lazy",
                })
                self.assertTrue(all("giscus.app" not in src for src in parser.scripts))

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
        sources = ["index.qmd", "content/academic/apr.qmd", "content/research/visits/liverpool.qmd",
                   "authors/kai-wu.qmd"]
        deployments = [SITE, "https://preview.example.org/projects/feature/",
                       "http://127.0.0.1:8765/", "http://localhost:8080/review/guide/"]
        for source in sources:
            for lang, prefix, alternate_prefix, alternate_lang in [("zh-CN", "", "en/", "en"),
                                                                   ("en", "en/", "", "zh-CN")]:
                with self.subTest(source=source, lang=lang):
                    parser, _, _ = self.parse(input_file=source, lang=lang, site=SITE + prefix,
                                              source_prefix=prefix)
                    switches = [link for link in parser.anchors
                                if "guide-language-switch" in link.get("class", "").split()]
                    self.assertEqual(len(switches), 1)
                    switch = switches[0]
                    page = source.replace(".qmd", ".html")
                    relative = "../" * source.count("/")
                    self.assertEqual(switch["href"], relative + ("../" if lang == "en" else "en/") + page)
                    self.assertEqual(switch["hreflang"], alternate_lang)
                    self.assertEqual(switch["target"], "_self")
                    self.assertIn("no-external", switch.get("class", "").split())
                    self.assertIn("data-noresolveinput", switch)
                    for deployment in deployments:
                        current = urljoin(deployment, prefix + page)
                        self.assertEqual(urljoin(current, switch["href"]),
                                         urljoin(deployment, alternate_prefix + page))

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
                self.assertEqual(parser.scripts, [self.versioned_script(script)])

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
        self.assertEqual(source[0]["href"], "../../../content/milestones/apr.html")
        self.assertEqual(source[0]["target"], "_self")
        self.assertIn("no-external", source[0].get("class", "").split())
        self.assertIn("data-noresolveinput", source[0])


if __name__ == "__main__":
    unittest.main()
