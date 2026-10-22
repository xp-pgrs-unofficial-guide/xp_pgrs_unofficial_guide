"""Verify the shared update timeline through the production Pandoc filters."""

import copy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
FILTER = ROOT / "book/filters/updates.lua"
BODY = "## Recent updates {#recent-updates}\n\n::: {.guide-updates}\n:::\n"
RECORDS = [
    {"id": "2026-10-22-new-log", "date": "2026-10-22", "type": "site",
     "summary": {"zh-CN": "新增简短更新记录。", "en": "Add short update records."},
     "articles": [{"path": "content/about/changelog.qmd", "anchor": "xp-guide-changelog",
                   "title": {"zh-CN": "更新日志", "en": "Changelog"}}]},
    {"id": "2026-10-22-content", "date": "2026-10-22", "type": "content",
     "summary": {"zh-CN": "补充毕业准备经验。", "en": "Expand graduation preparation advice."},
     "articles": [{"path": "content/study/graduation.qmd", "anchor": "xp-guide-graduation",
                   "title": {"zh-CN": "毕业流程", "en": "Graduation process"}},
                  {"path": "content/resources/it-services.qmd", "anchor": "xp-guide-legacy-vm",
                   "title": {"zh-CN": "校园 IT 服务", "en": "Campus IT services"}}]},
    {"id": "2026-09-01-site", "date": "2026-09-01", "type": "site",
     "summary": {"zh-CN": "改进网站搜索。", "en": "Improve site search."}, "articles": []},
]
HISTORY = {
    "zh-CN": (
        "- v0.1 on 2022/8/9：完成项目创建，确定模板，构建GitHub Actions自动在线编译并发布",
        r"- v0.2 on 2022/10/12：完成\[必做\]、\[福利\]两大章节的攻略内容，包括必修课程、会议记录、APR、会议经费、办公用品、打印、体育馆",
        r"- v0.3 on 2022/11/18：完成\[最好要知道\]章节的绝大部分内容：TA的改作业、监考、lab，Symposium（移动到\[必做\]章）",
        "- v0.4 on 2023/03/01：新增电脑备份攻略、腰椎颈椎攻略、学生证相关攻略、常用信息导航",
        "- v1.0 on 2024/08/12：补完毕业章节",
        "- v1.1 on 2024/10/21：新增 [学术研究是怎么发生的](../research/how-research-works.qmd#section.how-research-works)、 [利物浦访学](../research/liverpool-visit.qmd#section.UoL_visit)",
    ),
    "en": (
        "- v0.1 on 2022/8/9: created the project, chose the template, and set up GitHub Actions for automatic online compilation and publication.",
        r"- v0.2 on 2022/10/12: completed the \[Must do\] and \[Benefits\] chapters, covering compulsory courses, meeting records, APR, conference funding, office supplies, printing, and sports facilities.",
        r"- v0.3 on 2022/11/18: completed most of the \[Good to know\] chapter: marking, invigilation, and lab work as a TA, plus the Symposium, which was moved to the \[Must do\] chapter.",
        "- v0.4 on 2023/03/01: added guides to computer backups, lower back and neck care, student cards, and a directory of useful information.",
        "- v1.0 on 2024/08/12: completed the graduation chapter.",
        "- v1.1 on 2024/10/21: added [How academic research happens](../research/how-research-works.qmd#section.how-research-works) and [Visiting Liverpool](../research/liverpool-visit.qmd#section.UoL_visit).",
    ),
}


class Timeline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.events = []
        self.months = []
        self.links = []
        self.contributions = 0
        self.div_stack = []

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == "div":
            classes = fields.get("class", "").split()
            if "guide-update" in classes:
                self.events.append(fields)
            self.div_stack.append(classes)
        if tag == "h3":
            self.months.append((fields.get("id"), any("contribution" in classes for classes in self.div_stack)))
        if tag == "a":
            self.links.append(fields.get("href"))

    def handle_endtag(self, tag):
        if tag == "div":
            self.div_stack.pop()


def convert(records=RECORDS, lang="zh-CN", output_format="html5", *, body=BODY,
            source="content/about/changelog.qmd", attribution=True, metadata=None, quarto_input=None):
    meta = {"lang": lang, "guide-updates": records, "guide-page-path": source,
            "guide-updates-page": True, "guide-authors": {"editorial": "项目编辑组"},
            "guide-authors-en": {"editorial": "Editorial team"}}
    meta.update(metadata or {})
    meta = {key: value for key, value in meta.items() if value is not None}
    text = "---\n" + json.dumps(meta, ensure_ascii=False) + "\n---\n\n" + body
    pandoc = os.environ.get("PANDOC_BIN")
    command = [pandoc] if pandoc else [os.environ.get("QUARTO_BIN", "quarto"), "pandoc"]
    environment = os.environ.copy()
    renderer = FILTER
    if quarto_input:
        environment["GUIDE_TEST_INPUT"] = quarto_input
        environment["GUIDE_TEST_PUBLISHING_FILTER"] = str(FILTER)
        renderer = ROOT / "tests/publishing/quarto_stub.lua"
    command += ["--from=markdown", "--wrap=none", "--to=" + output_format, "--lua-filter=" + str(renderer)]
    if attribution:
        command.append("--lua-filter=" + str(ROOT / "book/filters/attribution.lua"))
    if output_format == "gfm":
        command.append("--lua-filter=" + str(ROOT / "book/filters/markdown-export.lua"))
    return subprocess.run(command, input=text, text=True, capture_output=True, cwd=ROOT, env=environment)


class UpdateTimelineTests(unittest.TestCase):
    def render(self, **options):
        result = convert(**options)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_month_groups_preserve_record_order_and_same_day_events(self):
        for lang, heading in (("zh-CN", "2026 年 10 月"), ("en", "October 2026")):
            with self.subTest(lang=lang):
                output = self.render(lang=lang)
                timeline = Timeline()
                timeline.feed(output)
                self.assertEqual(timeline.months, [("updates-2026-10", False), ("updates-2026-09", False)])
                self.assertIn(heading, output)
                self.assertEqual([event["id"] for event in timeline.events], ["update-" + record["id"] for record in RECORDS])
                self.assertEqual(output.count('class="guide-update-date">2026-10-22'), 2)
                for record in RECORDS:
                    self.assertEqual(output.count(record["summary"][lang]), 1)
                    self.assertNotIn(record["summary"]["en" if lang == "zh-CN" else "zh-CN"], output)

    def test_html_uses_localized_labels_links_and_compatible_attribution(self):
        for lang, labels in (("zh-CN", ("内容更新", "网站改进", "相关文章：")),
                             ("en", ("Content update", "Site improvement", "Related articles: "))):
            with self.subTest(lang=lang):
                output = self.render(lang=lang)
                timeline = Timeline()
                timeline.feed(output)
                for label in labels:
                    self.assertIn(label, output)
                for event in timeline.events:
                    self.assertEqual(event["data-author-ids"], "editorial")
                    self.assertEqual(event["data-attribution-status"], "confirmed")
                self.assertIn("changelog.qmd#xp-guide-changelog", timeline.links)
                self.assertIn("../study/graduation.qmd#xp-guide-graduation", timeline.links)
                self.assertIn("../resources/it-services.qmd#xp-guide-legacy-vm", timeline.links)
                self.assertNotIn("Related articles: </span>", output)

    def test_pdf_has_internal_article_links_and_event_destinations(self):
        output = self.render(output_format="latex", lang="en")
        self.assertIn(r"\hyperref[xp-guide-graduation]{Graduation process}", output)
        self.assertIn(r"\hyperref[xp-guide-legacy-vm]{Campus IT services}", output)
        self.assertNotIn(".qmd", output)
        for record in RECORDS:
            self.assertIn(r"\label{update-" + record["id"] + "}", output)
            self.assertEqual(output.count(record["summary"]["en"]), 1)

    def test_markdown_keeps_plain_readable_content_and_destinations(self):
        output = self.render(output_format="gfm", lang="en")
        self.assertIn("[Graduation process](../study/graduation.qmd#xp-guide-graduation)", output)
        self.assertIn("[Campus IT services](../resources/it-services.qmd#xp-guide-legacy-vm)", output)
        self.assertIn("**2026-10-22 · Content update**", output)
        self.assertNotIn("guide-update", output)
        self.assertNotIn("<div", output)
        for record in RECORDS:
            self.assertEqual(output.count('<a id="update-' + record["id"] + '"></a>'), 1)

    def test_article_paths_follow_the_current_page_directory(self):
        output = self.render(source="index.qmd")
        self.assertIn('href="content/study/graduation.qmd#xp-guide-graduation"', output)
        output = self.render(source="content/deep/more/changelog.qmd")
        self.assertIn('href="../../study/graduation.qmd#xp-guide-graduation"', output)

    def test_quarto_rebased_metadata_paths_are_not_made_relative_twice(self):
        records = copy.deepcopy(RECORDS)
        for record in records:
            for article in record["articles"]:
                article["path"] = "../../" + article["path"]
        for lang, prefix in (("zh-CN", ""), ("en", "en/")):
            with self.subTest(lang=lang):
                output = self.render(records=records, lang=lang, metadata={"guide-page-path": None},
                                     quarto_input=str(ROOT / "book" / prefix / "content/about/changelog.qmd"))
                self.assertIn('href="../study/graduation.qmd#xp-guide-graduation"', output)
                self.assertIn('href="changelog.qmd#xp-guide-changelog"', output)
                self.assertNotIn("../../../../content/", output)

    def test_empty_timeline_and_non_update_pages(self):
        for lang, message in (("zh-CN", "暂无更新记录。"), ("en", "No updates recorded yet.")):
            output = self.render(records=[], lang=lang)
            self.assertIn(message, output)
            self.assertNotIn("<h3", output)
            self.assertNotIn("Related articles", output)
        output = self.render(body="An ordinary article.")
        self.assertEqual(output.strip(), "<p>An ordinary article.</p>")

    def test_missing_generated_data_fails_only_when_placeholder_is_present(self):
        result = convert(metadata={"guide-updates": None})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing guide-updates metadata", result.stderr)
        output = self.render(body="An ordinary article.", metadata={"guide-updates": None})
        self.assertIn("An ordinary article.", output)

    def test_summary_punctuation_is_readable_in_html(self):
        records = copy.deepcopy(RECORDS[:1])
        records[0]["summary"]["en"] = 'Improve search & article links.'
        output = self.render(records=records, lang="en")
        self.assertIn("Improve search &amp; article links.", output)

    def test_original_history_and_page_identity_are_preserved(self):
        for lang, prefix in (("zh-CN", ""), ("en", "en/")):
            with self.subTest(lang=lang):
                source = (ROOT / "book" / prefix / "content/about/changelog.qmd").read_text(encoding="utf-8")
                self.assertEqual(tuple(re.findall(r"^- v[^\n]+", source, re.MULTILINE)), HISTORY[lang])
                self.assertIn("discussion-id: xp-guide-changelog", source)
                self.assertIn("{#xp-guide-changelog}", source)
                self.assertIn("{#historical-milestones}", source)
                self.assertLess(source.index("{#recent-updates}"), source.index("- v0.1"))
                self.assertGreater(source.index("{#changelog-more-links}"), source.index("- v1.1"))
                self.assertIn("https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/releases", source)


if __name__ == "__main__":
    unittest.main()
