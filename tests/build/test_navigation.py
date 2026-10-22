"""Exercise topic navigation and a PDF order derived from the same source tree."""

from copy import deepcopy
import json
from unittest.mock import patch

import yaml

from scripts import build
from test_content_paths import TemporaryBook


class NavigationTests(TemporaryBook):
    def tree(self):
        return [
            "index.qmd",
            {"part": "学业", "contents": [
                {"section": "培养要求与考核", "contents": ["content/milestones/apr.qmd"]},
                {"section": "content/resources/funding.qmd", "contents": [
                    {"href": "content/appendix/contributing.qmd", "text": "Contribute"}]}]},
        ]

    def test_three_level_navigation_includes_clickable_groups_and_href_leaves_once(self):
        tree = self.tree()
        build.validate_navigation(tree)
        self.assertEqual(list(build.chapters(tree)), list(self.articles))
        original = deepcopy(tree)
        self.assertEqual(build.pdf_chapters(tree), [
            "index.qmd", {"part": "学业", "chapters": list(self.articles)[1:]}])
        self.assertEqual(tree, original)

    def test_pdf_parts_keep_their_own_article_without_repeating_it_as_a_child(self):
        tree = ["index.qmd", {"part": "content/milestones/apr.qmd", "contents": [
            {"section": "Resources", "contents": list(self.articles)[2:]}]}]
        flattened = build.pdf_chapters(tree)
        self.assertEqual(flattened[1], {"part": "content/milestones/apr.qmd", "chapters": list(self.articles)[2:]})
        self.assertEqual(list(build.chapters(flattened)), list(self.articles))

    def test_malformed_tree_is_rejected_before_quarto_can_ignore_its_children(self):
        invalid = [
            {"part": "Academic", "contents": ["index.qmd"]},
            [42],
            ["https://example.test/article.qmd"],
            [{"href": "index.qmd", "menu": ["content/milestones/apr.qmd"]}],
            [{"part": "Academic", "content": ["index.qmd"]}],
            [{"part": "Academic", "chapters": [], "contents": []}],
            [{"part": "Academic", "contents": "index.qmd"}],
            [{"part": "Academic", "contents": None}],
            [{"part": "Academic", "contents": [{"part": "Milestones", "contents": ["index.qmd"]}]}],
            [{"part": "Academic", "chapters": [{"section": "Milestones", "contents": ["index.qmd"]}]}],
            [{"part": "Academic", "contents": [{"section": "Milestones", "chapters": ["index.qmd"]}]}],
            [{"part": "Academic", "contents": [{"href": "../index.qmd"}]}],
            [{"part": "Academic", "contents": [{"href": "index.qmd", "text": ""}]}],
        ]
        for tree in invalid:
            with self.subTest(tree=tree), self.assertRaisesRegex(ValueError, "目录|三级"):
                build.validate_navigation(tree)

    def test_source_coverage_rejects_duplicate_or_missing_articles_in_nested_groups(self):
        for contents in (["index.qmd", "index.qmd"], list(self.articles)[:-1]):
            self.config["book"]["chapters"] = [{"part": "Academic", "contents": [
                {"section": "Milestones", "contents": contents}]}]
            (self.book / "_quarto.yml").write_text(yaml.safe_dump(self.config))
            with self.subTest(contents=contents), self.assertRaisesRegex(ValueError, "目录与正文不一致"):
                build.validate_sources("unused")

    def test_pdf_project_is_temporary_and_does_not_change_the_authored_config(self):
        self.config["book"]["chapters"] = self.tree()
        config_path = self.book / "_quarto.yml"
        config_path.write_text(yaml.safe_dump(self.config))
        original = config_path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "render failed"):
            with build.pdf_project(self.book) as project:
                generated = project / "_quarto.yml"
                data = yaml.safe_load(generated.read_text())
                self.assertEqual(data["book"]["chapters"], build.pdf_chapters(self.tree()))
                self.assertEqual(data["project"]["output-dir"], str(self.output))
                self.assertEqual((project / "index.qmd").read_bytes(), (self.book / "index.qmd").read_bytes())
                self.assertEqual((project / "assets/figure.png").read_bytes(), b"fixture asset")
                self.assertTrue((project / "filters/author-pages.lua").exists())
                self.assertFalse((project / "_book").exists())
                raise RuntimeError("render failed")
        self.assertEqual(config_path.read_bytes(), original)
        self.assertFalse(generated.exists())

    def test_author_profile_lists_articles_inside_nested_topics(self):
        profile = self.book / "authors/editorial.qmd"
        profile.parent.mkdir()
        profile.write_text('''---
title: Editors
discussion-id: xp-guide-author-editorial
guide-author-id: editorial
---
::: {#xp-guide-author-editorial}
:::
''')
        tree = self.tree() + [{"part": "Authors", "contents": ["authors/editorial.qmd"]}]
        self.config["book"]["chapters"] = tree
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(self.config))
        with patch.object(build, "run", self.pandoc_run):
            ast = build.pandoc_json("test-quarto", profile)
        links = []
        def visit(node):
            if isinstance(node, list):
                for child in node:
                    visit(child)
            elif isinstance(node, dict):
                if node.get("t") == "Link":
                    links.append(node["c"][-1][0])
                for child in node.values():
                    visit(child)
        visit(ast["blocks"])
        for path in self.articles:
            self.assertIn("../" + path, links)

    def test_global_anchor_check_ignores_code_examples_but_rejects_moved_copies(self):
        for relative in list(self.articles)[1:3]:
            path = self.book / relative
            path.write_text(path.read_text() + "\n::: {#shared-moved-section}\n:::\n")
        with patch.object(build, "run", self.pandoc_run):
            with self.assertRaisesRegex(ValueError, "全书锚点重复.*shared-moved-section"):
                self.quietly(build.validate_sources, "test-quarto")
        source = '''## Topic {#real-topic}

::: {.contribution authors="editorial"}
```markdown
## Example {#real-topic}
```
:::
'''
        ast = json.loads(self.pandoc_run(["test-quarto", "pandoc", "--from=markdown", "--to=json"],
                                        input=source, capture_output=True, text=True).stdout)
        self.assertEqual(build.document_identifiers(ast), ["real-topic"])
