"""Validate shared update records and build integration without Git or a server."""

from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from scripts import build
from scripts.updates import GENERATED_NAME
from test_content_paths import TemporaryBook


class UpdateDataTests(TemporaryBook):
    def mirror(self):
        for source in list(build.pages()):
            destination = self.book / "en" / source.relative_to(self.book)
            destination.parent.mkdir(parents=True, exist_ok=True)
            meta, body = build.frontmatter(source)
            meta["title"] = "English " + meta["title"]
            destination.write_text("---\n" + yaml.safe_dump(meta) + "---\n" + body, encoding="utf-8")
        (self.book / "en/_quarto.yml").write_text(yaml.safe_dump(self.config), encoding="utf-8")

    def write_update(self, slug="2026-10-22-new-log", **changes):
        record = {"date": "2026-10-22", "type": "content",
                  "summary": {"zh-CN": "补充年度考核经验。", "en": "Add annual review guidance."},
                  "articles": ["xp-guide-apr"]}
        record.update(changes)
        destination = self.book / "updates" / (slug + ".yml")
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(yaml.safe_dump(record, allow_unicode=True), encoding="utf-8")
        return destination

    def test_absent_directory_generates_an_empty_shared_list(self):
        self.assertEqual(build.prepare_updates(), [])
        self.assertEqual(yaml.safe_load((self.book / GENERATED_NAME).read_text()), {"guide-updates": []})

    def test_one_bilingual_record_resolves_current_titles_and_is_not_duplicated(self):
        self.mirror()
        self.write_update(date=date(2026, 10, 22))
        records = build.prepare_updates()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["id"], "2026-10-22-new-log")
        self.assertEqual(record["date"], "2026-10-22")
        self.assertEqual(record["articles"], [{"path": "content/milestones/apr.qmd", "anchor": "xp-guide-apr",
                                             "title": {"zh-CN": "Annual review", "en": "English Annual review"}}])
        persisted = yaml.safe_load((self.book / GENERATED_NAME).read_text())
        self.assertIsInstance(persisted["guide-updates"][0]["date"], str)
        self.assertEqual(persisted, {"guide-updates": records})

    def test_records_sort_by_date_then_slug_independent_of_creation_order(self):
        for slug, day in (("z-last", "2026-10-22"), ("first", "2026-10-23"),
                          ("a-first", "2026-10-22"), ("old", "2025-12-31")):
            self.write_update(slug, date=day, type="site", articles=[])
        self.assertEqual([record["id"] for record in build.prepare_updates()], ["first", "a-first", "z-last", "old"])

    def test_bad_dates_types_summaries_and_article_lists_are_rejected(self):
        cases = [
            ({"date": "2026-02-30"}, "有效日期"),
            ({"date": "2026-2-03"}, "YYYY-MM-DD"),
            ({"date": datetime(2026, 10, 22, 10)}, "YYYY-MM-DD"),
            ({"date": 20261022}, "YYYY-MM-DD"),
            ({"type": "misc"}, "content 或 site"),
            ({"summary": {"zh-CN": "只有中文"}}, "两种摘要"),
            ({"summary": {"zh-CN": "摘要", "en": "Summary.", "fr": "Extra."}}, "两种摘要"),
            ({"summary": {"zh-CN": "", "en": "Summary."}}, "一句话摘要"),
            ({"summary": {"zh-CN": "第一行\n第二行", "en": "Summary."}}, "一句话摘要"),
            ({"summary": {"zh-CN": "摘要", "en": " Summary. "}}, "一句话摘要"),
            ({"articles": "xp-guide-apr"}, "标识列表"),
            ({"articles": ["content/milestones/apr.qmd"]}, "标识列表"),
            ({"articles": ["xp-guide-apr", "xp-guide-apr"]}, "重复文章标识"),
            ({"articles": []}, "至少一篇文章"),
            ({"extra": True}, "只能包含"),
        ]
        for mutation, error in cases:
            with self.subTest(mutation=mutation):
                self.write_update(**mutation)
                with self.assertRaisesRegex(ValueError, error):
                    build.prepare_updates()

    def test_yaml_errors_missing_fields_and_duplicate_keys_report_the_source_file(self):
        cases = ["date: [\n", "date: 2026-02-30\n", "date: 2026-10-22\n", "date: 2026-10-22\ndate: 2026-10-23\n"]
        path = self.write_update(type="site", articles=[])
        for source in cases:
            with self.subTest(source=source):
                path.write_text(source)
                with self.assertRaises(ValueError) as caught:
                    build.prepare_updates()
                self.assertIn(str(path), str(caught.exception))

    def test_same_stem_across_yaml_extensions_and_invalid_slugs_are_rejected(self):
        path = self.write_update(type="site", articles=[])
        duplicate = path.with_suffix(".yaml")
        duplicate.write_text(path.read_text())
        with self.assertRaisesRegex(ValueError, "文件标识重复"):
            build.prepare_updates()
        duplicate.unlink()
        path.rename(path.with_name("Not stable.yml"))
        with self.assertRaisesRegex(ValueError, "文件名"):
            build.prepare_updates()

    def test_missing_article_in_either_language_is_an_error(self):
        self.mirror()
        self.write_update(articles=["xp-guide-missing"])
        with self.assertRaisesRegex(ValueError, "无法定位文章标识 xp-guide-missing"):
            build.prepare_updates()
        self.write_update()
        (self.book / "en/content/milestones/apr.qmd").unlink()
        with self.assertRaisesRegex(ValueError, "xp-guide-apr（en）"):
            build.prepare_updates()

    def test_move_and_rename_keep_the_record_and_use_the_current_bilingual_titles(self):
        self.mirror()
        self.write_update()
        for prefix, title in (("", "考核与评审"), ("en/", "Current review title")):
            source = self.book / prefix / "content/milestones/apr.qmd"
            target = self.book / prefix / "content/academic/review.qmd"
            target.parent.mkdir(parents=True)
            meta, body = build.frontmatter(source)
            meta["title"] = title
            target.write_text("---\n" + yaml.safe_dump(meta, allow_unicode=True) + "---\n" + body)
            source.unlink()
        article = build.prepare_updates()[0]["articles"][0]
        self.assertEqual(article, {"path": "content/academic/review.qmd", "anchor": "xp-guide-apr",
                                   "title": {"zh-CN": "考核与评审", "en": "Current review title"}})

    def test_merged_page_keeps_the_retired_article_anchor_and_current_title(self):
        self.mirror()
        self.write_update()
        for prefix in ("", "en/"):
            old = self.book / prefix / "content/milestones/apr.qmd"
            target = self.book / prefix / "content/resources/funding.qmd"
            target.write_text(target.read_text() + "\n::: {#xp-guide-apr}\n:::\n")
            old.unlink()
        article = build.prepare_updates()[0]["articles"][0]
        self.assertEqual(article["path"], "content/resources/funding.qmd")
        self.assertEqual(article["anchor"], "xp-guide-apr")
        self.assertEqual(article["title"], {"zh-CN": "Funding", "en": "English Funding"})

    def test_bilingual_aliases_must_resolve_to_the_same_page(self):
        self.mirror()
        self.write_update(articles=["xp-guide-retired"])
        for prefix, relative in (("", "content/milestones/apr.qmd"), ("en/", "content/resources/funding.qmd")):
            target = self.book / prefix / relative
            target.write_text(target.read_text() + "\n::: {#xp-guide-retired}\n:::\n")
        with self.assertRaisesRegex(ValueError, "中英文承接路径不一致"):
            build.prepare_updates()

    def test_duplicate_aliases_in_one_or_multiple_pages_are_ambiguous(self):
        self.mirror()
        self.write_update()
        target = self.book / "content/resources/funding.qmd"
        original = target.read_text()
        for extra in ("::: {#xp-guide-apr}\n:::", "::: {#xp-guide-retired}\n:::\n::: {#xp-guide-retired}\n:::"):
            with self.subTest(extra=extra):
                target.write_text(original + "\n" + extra + "\n")
                with self.assertRaisesRegex(ValueError, "重复或存在歧义"):
                    build.prepare_updates()

    def test_anchor_examples_in_code_do_not_become_retired_article_ids(self):
        self.mirror()
        self.write_update()
        target = self.book / "content/resources/funding.qmd"
        target.write_text(target.read_text() + "\n```markdown\n::: {#xp-guide-apr}\n:::\n```\n\n`{#xp-guide-apr}`\n")
        self.assertEqual(build.prepare_updates()[0]["articles"][0]["anchor"], "xp-guide-apr")

    def test_invalid_record_does_not_overwrite_last_generated_data_and_source_checks_fail_early(self):
        self.write_update(type="site", articles=[])
        build.prepare_updates()
        generated = self.book / GENERATED_NAME
        previous = generated.read_bytes()
        self.write_update(type="invalid", articles=[])
        with patch.object(build, "run", side_effect=AssertionError("Pandoc must not run")):
            with self.assertRaisesRegex(ValueError, "content 或 site"):
                build.validate_sources("test-quarto")
        self.assertEqual(generated.read_bytes(), previous)

    def test_english_config_prefixes_all_shared_metadata_files(self):
        self.mirror()
        config = deepcopy(self.config)
        config.update({"project": {"type": "book"}, "format": {"html": {}, "pdf": {}},
                       "metadata-files": ["_authors.yml", GENERATED_NAME]})
        (self.book / "_quarto.yml").write_text(yaml.safe_dump(config))
        (self.book / "_languages.yml").write_text("lang: en\n")
        build.prepare_english_config()
        english = yaml.safe_load((self.book / "en/_quarto.yml").read_text())
        self.assertEqual(english["metadata-files"], ["../_authors.yml", "../" + GENERATED_NAME])

    def test_pdf_snapshot_copies_exact_shared_update_data_for_both_languages(self):
        self.mirror()
        self.write_update()
        for root in build.language_roots():
            with build.pdf_project(root) as staged:
                base = staged.parent if root.name == "en" else staged
                self.assertEqual((base / GENERATED_NAME).read_bytes(), (self.book / GENERATED_NAME).read_bytes())

    def test_pandoc_expands_only_flagged_pages_and_raw_checks_keep_the_placeholder(self):
        target = self.book / "content/appendix/contributing.qmd"
        meta, body = build.frontmatter(target)
        meta["guide-updates-page"] = True
        target.write_text("---\n" + yaml.safe_dump(meta) + "---\n" + body)
        result = SimpleNamespace(stdout=json.dumps({"blocks": [], "meta": {}}))
        with patch.object(build, "run", return_value=result) as run:
            build.pandoc_json("test-quarto", target)
            command = run.call_args.args[0]
            self.assertIn(f"--metadata-file={self.book / GENERATED_NAME}", command)
            self.assertIn("--metadata=guide-page-path:content/appendix/contributing.qmd", command)
            self.assertIn(f"--lua-filter={self.book / 'filters/updates.lua'}", command)
            build.pandoc_json("test-quarto", target, expand_author_pages=False)
            self.assertFalse(any(str(item).startswith("--lua-filter=") for item in run.call_args.args[0]))
            build.pandoc_json("test-quarto", self.book / "index.qmd")
            self.assertFalse(any(str(item).startswith("--lua-filter=") for item in run.call_args.args[0]))
