"""Exercise bilingual source parity and independent, readable language exports."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts import build
from test_content_paths import TemporaryBook


class LanguageBuildTests(TemporaryBook):
    def mirror(self):
        """Prepare a small real bilingual source tree, with shared publication assets."""
        english = self.book / "en"
        english.mkdir(exist_ok=True)
        for source in list(build.pages()):
            meta, body = build.frontmatter(source)
            meta.update({"lang": "en", "translation-source": source.relative_to(self.book).as_posix(),
                         "translation-status": "draft",
                         "translation-source-sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
            relative = source.relative_to(self.book)
            destination = english / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n" +
                                   body.replace("../../assets/", "../../../assets/"), encoding="utf-8")
        config = deepcopy(self.config)
        config["lang"] = "en"
        config["guide-site"] += "en/"
        (english / "_quarto.yml").write_text(yaml.safe_dump(config), encoding="utf-8")

    def validate_sources(self):
        with patch.object(build, "run", self.pandoc_run):
            self.quietly(build.validate_sources, "test-quarto")

    def test_parallel_sources_allow_shared_discussion_ids_in_different_languages(self):
        self.mirror()
        self.assertEqual(len(build.pages()), 2 * len(self.articles))
        self.validate_sources()

    def test_missing_mirror_fails_instead_of_silently_publishing_partial_languages(self):
        self.mirror()
        (self.book / "en/content/milestones/apr.qmd").unlink()
        with self.assertRaisesRegex(ValueError, "目录与正文不一致|镜像不完整"):
            self.validate_sources()

    def test_english_content_without_its_home_page_is_not_silently_ignored(self):
        self.mirror()
        (self.book / "en/index.qmd").unlink()
        with self.assertRaisesRegex(ValueError, "缺少正文源文件"):
            self.validate_sources()

    def test_changed_chinese_source_requires_translation_review(self):
        self.mirror()
        self.write_source("content/milestones/apr.qmd", "A material new detail.")
        with self.assertRaisesRegex(ValueError, "译文已过期"):
            self.validate_sources()

    def test_translations_must_preserve_attribution_and_explicit_anchors(self):
        self.mirror()
        target = self.book / "en/content/milestones/apr.qmd"
        original = target.read_text()
        mutations = [
            (original.replace("lang: en", "lang: zh-CN"), "必须设置 lang: en"),
            (original.replace('authors="editorial"', 'authors="editorial" contributors="editorial"'), "原作者、补充者或归属状态"),
            (original + "\n::: {#lost-in-translation}\n:::\n", "显式锚点"),
            (original.replace("translation-source: content/milestones/apr.qmd", "translation-source: index.qmd"), "translation-source 应为"),
        ]
        for text, error in mutations:
            with self.subTest(error=error):
                target.write_text(text)
                with self.assertRaisesRegex(ValueError, error):
                    self.validate_sources()
        target.write_text(original)
        self.validate_sources()

    def test_translated_headings_need_matching_ids_even_without_explicit_anchor_syntax(self):
        self.write_source("content/milestones/apr.qmd", "A paragraph.")
        source = self.book / "content/milestones/apr.qmd"
        source.write_text(source.read_text().replace('::: {.contribution', '## 新章节\n\n::: {.contribution'))
        self.mirror()
        target = self.book / "en/content/milestones/apr.qmd"
        target.write_text(target.read_text().replace("## 新章节", "## New section"))
        with self.assertRaisesRegex(ValueError, "中英文标题定位不一致"):
            self.validate_sources()

    def test_source_headings_in_credit_blocks_are_rejected_in_both_languages(self):
        self.mirror()
        for prefix in ("", "en/"):
            path = self.book / prefix / "content/milestones/apr.qmd"
            original = path.read_text()
            path.write_text(original.replace("CURRENT SOURCE TEXT", "## Misplaced section\n\nArticle text."))
            with self.subTest(language=prefix or "zh"):
                with self.assertRaisesRegex(ValueError, "标题必须放在署名内容块外") as error:
                    self.validate_sources()
                self.assertIn(str(path), str(error.exception))
            path.write_text(original)
        self.validate_sources()

    def test_author_metadata_does_not_hide_source_headings_but_template_headings_are_valid(self):
        relative = "authors/editorial.qmd"
        self.articles[relative] = ("Editors", "xp-guide-author-editorial")
        self.write_source(relative, '::: {.guide-author-profile data-guide-author-id="editorial"}\n:::')
        source = self.book / relative
        meta, body = build.frontmatter(source)
        meta["guide-author-id"] = "editorial"
        source.write_text("---\n" + yaml.safe_dump(meta) + "---\n" + body)
        self.config["book"]["chapters"] = list(self.articles)
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(self.config))
        self.mirror()
        self.validate_sources()  # The shared template generates “Credited articles” within the placeholder.
        for prefix in ("", "en/"):
            path = self.book / prefix / relative
            original = path.read_text()
            path.write_text(original.replace('::: {.guide-author-profile', '## Authored heading\n\n::: {.guide-author-profile'))
            with self.subTest(language=prefix or "zh"):
                with self.assertRaisesRegex(ValueError, "标题必须放在署名内容块外") as error:
                    self.validate_sources()
                self.assertIn(str(path), str(error.exception))
            path.write_text(original)

    def test_markdown_and_search_stay_in_their_language_with_shared_images(self):
        self.write_source("content/milestones/apr.qmd", "\n\n".join([
            "CHINESE SOURCE ONLY",
            "[Funding](../resources/funding.qmd#xp-guide-funding)",
            "![Figure](../../assets/figure.png)",
            "[Markdown index](../../llms.txt)",
        ]))
        self.mirror()
        translated = self.book / "en/content/milestones/apr.qmd"
        translated.write_text(translated.read_text().replace("CHINESE SOURCE ONLY", "ENGLISH TRANSLATION ONLY"))
        with patch.object(build, "run", self.pandoc_run):
            self.quietly(build.export_markdown, "test-quarto")
            self.quietly(build.validate_markdown, "test-quarto")
        english = self.output / "en/markdown/content/milestones/apr.md"
        text = english.read_text()
        for url in ("../resources/funding.md#xp-guide-funding", "../../../../assets/figure.png", "../../../llms.txt"):
            self.assertIn(url, text)
        self.assertIn("English translation draft", text)
        chinese_search = (self.output / "search.json").read_text()
        english_search = (self.output / "en/search.json").read_text()
        self.assertNotIn("ENGLISH TRANSLATION ONLY", chinese_search)
        self.assertNotIn("CHINESE SOURCE ONLY", english_search)
        for relative in ("llms.txt", "en/llms.txt"):
            index = (self.output / relative).read_text()
            self.assertIn("markdown/content/milestones/apr.md", index)
            self.assertNotIn("markdown/en/", index)

    def test_legacy_author_directory_redirects_keep_markdown_in_each_language(self):
        self.write_source("index.qmd", "[Old author directory](authors/index.qmd)")
        self.mirror()
        self.write_redirects({"authors/index.qmd": "index.qmd",
                              "en/authors/index.qmd": "en/index.qmd"})
        self.write_html()
        for relative, (_, identifier) in self.articles.items():
            target = self.output / "en" / Path(relative).with_suffix(".html")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f'<h1 id="{identifier}">English article</h1>')
        for prefix in ("", "en/"):
            home = self.output / prefix / "index.html"
            home.write_text(home.read_text() +
                            '<a href="authors/index.html#xp-guide-home">Old author directory</a>')
        with patch.object(build, "run", self.pandoc_run):
            self.quietly(build.export_markdown, "test-quarto")
            self.quietly(build.export_redirects)
            self.quietly(build.validate_output, html_only=True)
            self.quietly(build.validate_markdown, "test-quarto")
        mapping = build.redirect_outputs(".md")
        for prefix in ("", "en/"):
            directory = self.output / prefix / "markdown"
            alias = directory / "authors/index.md"
            self.assertEqual(mapping[alias], directory / "index.md")
            self.assertIn("(../index.md)", alias.read_text())
            self.assertIn("authors/index.md", (directory / "index.md").read_text())
        self.assertFalse((self.output / "markdown/en").exists())
        english_html = (self.output / "en/authors/index.html").read_text()
        self.assertIn(self.config["guide-site"] + "en/index.html", english_html)

    def test_generated_english_config_preserves_shared_navigation_and_theme(self):
        self.mirror()
        config = deepcopy(self.config)
        config.update({"project": {"type": "book", "output-dir": "_book", "resources": ["assets/**"]},
                       "filters": ["filters/attribution.lua"],
                       "format": {"html": {"theme": {"light": "cosmo", "dark": "darkly"},
                                            "respect-user-color-scheme": True}, "pdf": {}}})
        config["book"]["chapters"] = ["index.qmd", {"part": "里程碑", "chapters": list(self.articles)[1:]}]
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(config))
        (self.book / "_languages.yml").write_text(yaml.safe_dump({"book": {"title": "English Guide"},
                                                                  "parts": {"里程碑": "Milestones"}, "lang": "en"}))
        build.prepare_english_config()
        english = yaml.safe_load((self.book / "en/_quarto.yml").read_text())
        self.assertEqual(english["project"]["output-dir"], "../_book/en")
        self.assertNotIn("resources", english["project"])
        self.assertEqual(english["book"]["title"], "English Guide")
        self.assertEqual(english["book"]["chapters"][1]["part"], "Milestones")
        self.assertEqual(english["book"]["repo-subdir"], "book/en")
        self.assertEqual(english["format"]["html"]["theme"], config["format"]["html"]["theme"])
        self.assertTrue(english["format"]["html"]["respect-user-color-scheme"])
        self.assertEqual(english["filters"], ["../filters/attribution.lua"])
        self.assertEqual(english["format"]["pdf"]["include-in-header"], "../pdf/style.tex")
        self.assertIn("scheme=plain", english["format"]["pdf"]["classoption"])
        self.assertEqual(english["guide-site-root"], self.config["guide-site"])
        self.assertEqual(english["guide-site"], self.config["guide-site"] + "en/")

    def test_file_valued_parts_are_validated_once_and_remain_shared_in_english(self):
        self.mirror()
        config = deepcopy(self.config)
        config.update({"project": {"type": "book", "output-dir": "_book"},
                       "format": {"html": {}, "pdf": {}}})
        config["book"]["chapters"] = [
            "index.qmd", {"part": "content/milestones/apr.qmd", "chapters": list(self.articles)[2:]}]
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(config))
        (self.book / "_languages.yml").write_text("lang: en\n")
        build.prepare_english_config()
        english = yaml.safe_load((self.book / "en/_quarto.yml").read_text())
        self.assertEqual(list(build.chapters(config["book"]["chapters"])), list(self.articles))
        self.assertEqual(english["book"]["chapters"][1]["part"], "content/milestones/apr.qmd")
        self.validate_sources()

    def test_nested_topic_names_are_translated_without_changing_file_valued_groups(self):
        self.mirror()
        config = deepcopy(self.config)
        config.update({"project": {"type": "book", "output-dir": "_book"},
                       "format": {"html": {}, "pdf": {}}})
        config["book"]["chapters"] = ["index.qmd", {"part": "学业", "contents": [
            {"section": "培养考核", "contents": ["content/milestones/apr.qmd"]},
            {"section": "content/resources/funding.qmd", "contents": [
                {"href": "content/appendix/contributing.qmd"}]}]}]
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(config))
        (self.book / "_languages.yml").write_text(yaml.safe_dump({"lang": "en", "parts": {
            "学业": "Academic", "培养考核": "Requirements and reviews",
            "content/resources/funding.qmd": "Not a group title"}}))
        build.prepare_english_config()
        english = yaml.safe_load((self.book / "en/_quarto.yml").read_text())
        group = english["book"]["chapters"][1]
        self.assertEqual(group["part"], "Academic")
        self.assertEqual(group["contents"][0]["section"], "Requirements and reviews")
        self.assertEqual(group["contents"][1]["section"], "content/resources/funding.qmd")
        self.assertEqual(list(build.chapters(english["book"]["chapters"])), list(self.articles))
        self.validate_sources()

    def test_english_pdf_snapshot_preserves_shared_paths_and_author_article_links(self):
        self.mirror()
        english = self.book / "en"
        config = yaml.safe_load((english / "_quarto.yml").read_text())
        config["book"]["chapters"] = ["index.qmd", {"part": "Academic", "contents": [
            {"section": "Reviews", "contents": list(self.articles)[1:]}]}]
        config["metadata-files"] = ["../_authors.yml"]
        config["filters"] = ["../filters/author-pages.lua"]
        (english / "_quarto.yml").write_text(yaml.safe_dump(config))
        with build.pdf_project(english) as project:
            snapshot = yaml.safe_load((project / "_quarto.yml").read_text())
            self.assertEqual(snapshot["project"]["output-dir"], str(self.output / "en"))
            self.assertEqual(list(build.chapters(snapshot["book"]["chapters"])), list(self.articles))
            self.assertTrue((project / "../_authors.yml").resolve().exists())
            self.assertTrue((project / "../filters/author-pages.lua").resolve().exists())
            self.assertEqual((project / "../assets/figure.png").read_bytes(), b"fixture asset")
            self.assertEqual((project / "content/milestones/apr.qmd").read_bytes(),
                             (english / "content/milestones/apr.qmd").read_bytes())

    def test_output_validator_rejects_a_search_index_with_another_language_prefix(self):
        self.mirror()
        self.write_html()
        records = []
        for relative, (_, identifier) in self.articles.items():
            target = self.output / "en" / Path(relative).with_suffix(".html")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f'<h1 id="{identifier}">English article</h1>')
            records.append({"href": str(Path(relative).with_suffix(".html")), "text": "English"})
        index = self.output / "en/search.json"
        index.write_text(json.dumps(records))
        self.quietly(build.validate_output, html_only=True)
        records[0]["href"] = "en/index.html"
        index.write_text(json.dumps(records))
        with self.assertRaisesRegex(ValueError, "混入其他语言"):
            self.quietly(build.validate_output, html_only=True)

    def test_author_pages_expand_before_exporting_dynamic_article_links(self):
        (self.book / "_authors.yml").write_text("guide-authors:\n  editorial: Editors\n  unknown: Unconfirmed\n")
        for identifier in ("index", "editorial", "unknown"):
            relative = f"authors/{identifier}.qmd"
            self.articles[relative] = ("Authors", "xp-guide-author-" + identifier)
            self.write_source(relative)
            path = self.book / relative
            meta, body = build.frontmatter(path)
            meta["guide-author-index" if identifier == "index" else "guide-author-id"] = True if identifier == "index" else identifier
            path.write_text("---\n" + yaml.safe_dump(meta) + "---\n" + body)
        self.config["book"]["chapters"] = list(self.articles)
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(self.config))
        self.mirror()
        with patch.object(build, "run", self.pandoc_run):
            self.quietly(build.export_markdown, "test-quarto")
            self.quietly(build.validate_markdown, "test-quarto")
        text = (self.output / "en/markdown/authors/editorial.md").read_text()
        self.assertIn("Credited articles", text)
        self.assertIn("../content/milestones/apr.md", text)
        self.assertNotIn(".qmd", text)

    def test_multiple_profile_placeholders_expand_in_place_in_one_combined_document(self):
        (self.book / "_authors.yml").write_text("guide-authors:\n  editorial: Editors\n  unknown: Unconfirmed\n")
        funding = self.book / "content/resources/funding.qmd"
        funding.write_text(funding.read_text().replace('authors="editorial"', 'authors="unknown"'))
        document = """:::: {.contribution authors="editorial"}
Before the first profile.

::: {#profile-editors .guide-author-profile data-guide-author-id="editorial"}
:::

Between the profiles.

::: {#profile-unconfirmed .guide-author-profile data-guide-author-id="unknown"}
:::

After the second profile.
::::
"""
        command = ["test-quarto", "pandoc", "--from=markdown", "--to=json",
                   f"--metadata-file={self.book / '_quarto.yml'}",
                   f"--metadata-file={self.book / '_authors.yml'}",
                   f"--metadata=guide-source-root:{self.book}",
                   f"--lua-filter={self.book / 'filters/author-pages.lua'}"]
        result = self.pandoc_run(command, input=document, capture_output=True, text=True)
        ast = json.loads(result.stdout)
        self.assertNotIn("guide-author-id", ast["meta"])
        outer = ast["blocks"][0]
        self.assertIn("contribution", outer["c"][0][1])
        children = outer["c"][1]
        self.assertEqual([child["t"] for child in children], ["Para", "Div", "Para", "Div", "Para"])
        first, second = children[1], children[3]
        self.assertEqual(first["c"][0][0], "profile-editors")
        self.assertEqual(second["c"][0][0], "profile-unconfirmed")
        self.assertIn("../content/milestones/apr.qmd", json.dumps(first))
        self.assertNotIn("../content/resources/funding.qmd", json.dumps(first))
        self.assertIn("../content/resources/funding.qmd", json.dumps(second))
        self.assertNotIn("../content/milestones/apr.qmd", json.dumps(second))
        self.assertEqual(len(build.contribution_signatures(ast)), 1)
        latex = self.pandoc_run([*command[:3], "--to=latex", *command[4:]],
                                input=document, capture_output=True, text=True).stdout
        self.assertNotIn(".qmd", latex)
        self.assertIn("xp-guide-apr", latex)
        self.assertIn("xp-guide-funding", latex)

    def test_native_dual_theme_stylesheets_are_allowed_but_other_duplicate_ids_fail(self):
        parser = build.Links()
        for identifier in ("quarto-bootstrap", "quarto-text-highlighting-styles"):
            for classes in ("quarto-color-scheme", "quarto-color-scheme quarto-color-alternate", "quarto-color-scheme-extra"):
                parser.feed(f'<link rel="stylesheet" href="theme.css" class="{classes}" id="{identifier}">')
        self.assertEqual(parser.duplicate_ids, set())
        invalid = [
            '<div id="ordinary"></div><div id="ordinary"></div>',
            '<div id="quarto-bootstrap" class="quarto-color-scheme"></div><div id="quarto-bootstrap"></div>',
            '<link rel="stylesheet" class="quarto-color-scheme" id="quarto-bootstrap"><div id="quarto-bootstrap"></div>',
            '<div id="quarto-bootstrap"></div><link rel="stylesheet" class="quarto-color-scheme" id="quarto-bootstrap">',
            '<link rel="stylesheet" id="ordinary"><link rel="stylesheet" id="ordinary">',
            '<link rel="stylesheet" id="quarto-bootstrap"><link rel="stylesheet" id="quarto-bootstrap">',
        ]
        for markup in invalid:
            with self.subTest(markup=markup):
                parser = build.Links()
                parser.feed(markup)
                self.assertTrue(parser.duplicate_ids)
