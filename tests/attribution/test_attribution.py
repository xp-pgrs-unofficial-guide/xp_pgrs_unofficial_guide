"""Interoperability checks for the shared HTML/PDF/Markdown attribution filter.

Run with QUARTO_BIN=/path/to/quarto python3 -m unittest discover -s tests/attribution.
PANDOC_BIN=/path/to/pandoc also works when only Pandoc is installed.
No Python packages beyond the standard library are needed.
"""

import os
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
FILTER = ROOT / "book/filters/attribution.lua"
AUTHORS = ROOT / "book/_authors.yml"
QUARTO = os.environ.get("QUARTO_BIN", "quarto")
PANDOC = os.environ.get("PANDOC_BIN")


class AttributionHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def attributes(self, tag, class_name=None):
        return [attrs for element, attrs in self.elements
                if element == tag and (class_name is None or
                class_name in attrs.get("class", "").split())]


def convert(text, output_format):
    return subprocess.run(
        ([PANDOC] if PANDOC else [QUARTO, "pandoc"]) +
        ["--from=markdown", f"--to={output_format}",
         f"--metadata-file={AUTHORS}", f"--lua-filter={FILTER}"],
        input=text, text=True, capture_output=True, cwd=ROOT,
    )


class AttributionFilterTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "tests/attribution/sample.md").read_text()

    def test_html_shows_one_credit_per_run_without_rewriting_content(self):
        result = convert(self.source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('class="paragraph-attribution"'), 2)
        self.assertIn("<summary", result.stdout)
        self.assertIn("<table", result.stdout)
        self.assertIn('id="fig-example"', result.stdout)
        self.assertIn("具体段落归属待确认", result.stdout)
        self.assertIn("归属待确认", result.stdout)

    def test_identical_adjacent_authorship_continues_across_headings(self):
        source = '::: {.contribution authors="kai-wu"}\nFirst.\n:::\n\n## A heading\n\n::: {.contribution authors="kai-wu"}\nSecond.\n:::\n'
        result = convert(source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('class="paragraph-attribution"'), 1)
        self.assertEqual(result.stdout.count('data-author-ids="kai-wu"'), 2)
        blocks = AttributionHTML(result.stdout).attributes("div", "contribution")
        self.assertEqual([block["data-attribution-run"] for block in blocks], ["1", "1"])
        # Keeping the heading at root preserves Pandoc/Quarto's section and TOC
        # handling; a run must not introduce a wrapper around these siblings.
        self.assertIn('</div>\n<h2 id="a-heading">A heading</h2>\n<div', result.stdout)
        self.assertIn("Second.", result.stdout)
        self.assertIn('authors/kai-wu.html', result.stdout)

    def test_additions_confirmation_and_returning_author_start_new_runs(self):
        source = "\n\n".join(
            '::: {.contribution ' + attrs + '}\nText.\n:::'
            for attrs in ['authors="kai-wu"', 'authors="kai-wu" contributors="yue-zhou"',
                          'authors="kai-wu" contributors="yue-zhou" status="unverified"',
                          'authors="unknown"', 'authors="kai-wu"'])
        result = convert(source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('class="paragraph-attribution"'), 5)
        blocks = AttributionHTML(result.stdout).attributes("div", "contribution")
        self.assertEqual([block["data-attribution-run"] for block in blocks],
                         ["1", "2", "3", "4", "5"])

    def test_order_of_the_same_author_set_does_not_repeat_a_run(self):
        source = '::: {.contribution authors="kai-wu,yue-zhou"}\nFirst.\n:::\n\n::: {.contribution authors="yue-zhou,kai-wu"}\nSecond.\n:::\n'
        result = convert(source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('class="paragraph-attribution"'), 1)
        blocks = AttributionHTML(result.stdout).attributes("div", "contribution")
        self.assertEqual([block["data-attribution-run"] for block in blocks], ["1", "1"])

    def test_every_block_has_accessible_authorship_even_when_run_icon_is_hidden(self):
        source = '\n\n'.join(
            '::: {.contribution authors="kai-wu" contributors="yue-zhou" status="unverified"}\n' +
            text + '\n:::' for text in ["First.", "Second."])
        result = convert(source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        html = AttributionHTML(result.stdout)
        blocks = html.attributes("div", "contribution")
        expected_label = "原作者：吴开（Kai Wu）；实质补充：Yue Zhou；具体段落归属待确认"
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            self.assertEqual(block["role"], "group")
            self.assertEqual(block["aria-label"], expected_label)
        summaries = html.attributes("summary")
        self.assertEqual(len(summaries), 1)
        self.assertIn(expected_label, summaries[0]["aria-label"])
        icons = html.attributes("svg", "attribution-icon")
        self.assertEqual(len(icons), 1)
        self.assertEqual(icons[0]["aria-hidden"], "true")
        self.assertEqual(icons[0]["focusable"], "false")
        self.assertIn('class="attribution-label"', result.stdout)
        self.assertIn('class="attribution-scope">范围：右侧边线标出的连续内容。', result.stdout)
        self.assertIn('href="authors/kai-wu.html"', result.stdout)
        self.assertIn('href="authors/yue-zhou.html"', result.stdout)

    def test_english_labels_and_names_are_localized(self):
        result = convert('---\nlang: en\n---\n\n::: {.contribution authors="kai-wu"}\nText.\n:::\n', "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Original author", result.stdout)
        self.assertIn("By Kai Wu", result.stdout)
        self.assertNotIn("原作者", result.stdout)
        html = AttributionHTML(result.stdout)
        self.assertEqual(html.attributes("div", "contribution")[0]["aria-label"], "Original author: Kai Wu")
        self.assertIn("Original author: Kai Wu", html.attributes("summary")[0]["aria-label"])
        self.assertIn('class="attribution-scope">Scope: the continuous content marked by the right-hand boundary.', result.stdout)

    def test_markdown_export_preserves_names_without_web_controls(self):
        result = convert(self.source, "gfm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("吴开（Kai Wu）", result.stdout)
        self.assertIn("实质补充：Yue Zhou", result.stdout)
        self.assertIn("具体段落归属待确认", result.stdout)
        self.assertNotIn("<details", result.stdout)
        self.assertNotIn(".contribution", result.stdout)
        for marker in ["data-attribution-run", 'role="group"', "attribution-scope", "<svg"]:
            self.assertNotIn(marker, result.stdout)

    def test_latex_retains_attribution_and_content(self):
        result = convert(self.source, "latex")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("吴开（Kai Wu）", result.stdout)
        self.assertIn("A tight list item.", result.stdout)
        self.assertNotIn("<details", result.stdout)
        for marker in ["data-attribution-run", 'role="group"', "attribution-scope", "<svg"]:
            self.assertNotIn(marker, result.stdout)

    def test_unknown_author_fails_instead_of_silently_misattributing(self):
        result = convert('::: {.contribution authors="typo-author"}\nText.\n:::\n', "html5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown author ID 'typo-author'", result.stderr)

    def test_missing_author_requires_explicit_unknown(self):
        result = convert('::: {.contribution}\nText.\n:::\n', "html5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit authors attribute", result.stderr)


if __name__ == "__main__":
    unittest.main()
