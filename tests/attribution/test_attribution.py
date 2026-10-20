"""Interoperability checks for the shared HTML/PDF/Markdown attribution filter.

Run with QUARTO_BIN=/path/to/quarto python3 -m unittest discover -s tests/attribution.
PANDOC_BIN=/path/to/pandoc also works when only Pandoc is installed.
No Python packages beyond the standard library are needed.
"""

import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
FILTER = ROOT / "book/filters/attribution.lua"
AUTHORS = ROOT / "book/_authors.yml"
QUARTO = os.environ.get("QUARTO_BIN", "quarto")
PANDOC = os.environ.get("PANDOC_BIN")


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

    def test_html_attributes_paragraphs_lists_quotes_tables_and_figures(self):
        result = convert(self.source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('class="paragraph-attribution"'), 7)
        self.assertIn("<summary", result.stdout)
        self.assertIn("<table", result.stdout)
        self.assertIn('id="fig-example"', result.stdout)
        self.assertIn("具体段落归属待确认", result.stdout)
        self.assertIn("归属待确认", result.stdout)

    def test_markdown_export_preserves_names_without_web_controls(self):
        result = convert(self.source, "gfm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("吴开（Kai Wu）", result.stdout)
        self.assertIn("实质补充：Yue Zhou", result.stdout)
        self.assertIn("具体段落归属待确认", result.stdout)
        self.assertNotIn("<details", result.stdout)
        self.assertNotIn(".contribution", result.stdout)

    def test_latex_retains_attribution_and_content(self):
        result = convert(self.source, "latex")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("吴开（Kai Wu）", result.stdout)
        self.assertIn("A tight list item.", result.stdout)
        self.assertNotIn("<details", result.stdout)

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
