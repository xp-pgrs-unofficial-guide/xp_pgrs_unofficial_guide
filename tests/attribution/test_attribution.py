"""Interoperability checks for the shared HTML/PDF/Markdown attribution filter.

Run with QUARTO_BIN=/path/to/quarto python3 -m unittest discover -s tests/attribution.
PANDOC_BIN=/path/to/pandoc also works when only Pandoc is installed.
No Python packages beyond the standard library are needed.
"""

import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import unittest

from test_author_pages import ProfileMarkup


ROOT = Path(__file__).resolve().parents[2]
FILTER = ROOT / "book/filters/attribution.lua"
AUTHORS = ROOT / "tests/attribution/authors.yml"
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

    def test_profile_pages_keep_content_and_anchors_without_editorial_attribution_rails(self):
        for language in ["zh-CN", "en"]:
            source = ('---\nlang: ' + language + '\nguide-author-id: kai-wu\n---\n\n'
                      '::: {#profile-content .contribution authors="kai-wu"}\n'
                      'Profile details and public links.\n\n## Credited articles\n\n'
                      '[Article](../content/example.html)\n:::\n')
            result = convert(source, "html5")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('id="profile-content"', result.stdout)
            self.assertIn("Profile details and public links.", result.stdout)
            self.assertIn('href="../content/example.html"', result.stdout)
            for marker in ['class="contribution"', "paragraph-attribution", "attribution-icon",
                           "data-attribution-run", "data-author-ids", 'role="group"',
                           'authors="kai-wu"']:
                self.assertNotIn(marker, result.stdout)
            # Source attribution still survives printable and agent-readable
            # exports; suppression applies only to the webpage presentation.
            for output_format in ["gfm", "latex"]:
                exported = convert(source, output_format)
                self.assertEqual(exported.returncode, 0, exported.stderr)
                self.assertIn("Kai Wu", exported.stdout)

    def test_popovers_group_public_icons_with_their_author_or_contributor(self):
        metadata = {"guide-author-profiles": {
            "kai-wu": {"orcid": "0000-0002-1825-0097",
                       "google-scholar": "https://scholar.google.com/citations?user=example&hl=en",
                       "email": "kai@example.edu"},
            "yue-zhou": {"github": "https://github.com/example"},
        }}
        source = ('---\n' + json.dumps(metadata) + '\n---\n\n' +
                  '::: {.contribution authors="kai-wu,unknown" contributors="yue-zhou"}\nText.\n:::\n')
        result = convert(source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = ProfileMarkup(result.stdout)
        people = parsed.elements("span", "attribution-person")
        self.assertEqual([person["attributes"]["data-author-id"] for person in people],
                         ["kai-wu", "unknown", "yue-zhou"])
        expected = [{"orcid", "google-scholar", "email"}, set(), {"github"}]
        for person, kinds in zip(people, expected):
            links = parsed.elements("a", "guide-profile-link", root=person)
            self.assertEqual({link["attributes"]["data-profile-kind"] for link in links}, kinds)
            self.assertEqual(len(parsed.elements("span", "guide-profile-links-attribution", root=person)),
                             int(bool(kinds)), "unknown profiles should not render empty icon rows")
            self.assertEqual(len(parsed.elements("a", "attribution-person-name", root=person)), 1)
            for link in links:
                self.assertEqual(link["attributes"]["title"], link["attributes"]["aria-label"])
                self.assertIn(" — ", link["attributes"]["aria-label"])
                self.assertEqual(parsed.elements("span", "guide-profile-tooltip", root=link), [],
                                 "scrolling cards need their hints outside the link, in normal flow")
                self.assertEqual(len(parsed.elements("span", "guide-profile-print-label", root=link)), 1)
            for group in parsed.elements("span", "guide-profile-links-attribution", root=person):
                children = [child for child in group["children"] if isinstance(child, dict)]
                self.assertEqual(len(children), 2 * len(kinds))
                for index in range(0, len(children), 2):
                    self.assertEqual(children[index]["tag"], "a")
                    hint = children[index + 1]
                    self.assertIn("guide-profile-tooltip", hint["attributes"]["class"].split())
                    self.assertEqual(hint["attributes"]["aria-hidden"], "true")
                    self.assertIn(" ".join(ProfileMarkup.text(hint).split()), children[index]["attributes"]["aria-label"])
        email = next(link for link in parsed.elements("a", "guide-profile-link")
                     if link["attributes"]["data-profile-kind"] == "email")
        self.assertEqual(email["attributes"]["href"], "mailto:kai@example.edu")
        self.assertEqual(email["attributes"]["aria-label"], "吴开（Kai Wu） — 邮箱：kai@example.edu")
        for output_format in ["gfm", "latex"]:
            exported = convert(source, output_format)
            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertNotIn("guide-profile", exported.stdout)
            self.assertNotIn("mailto:", exported.stdout)
            self.assertIn("Yue Zhou", exported.stdout)

    def test_popover_icons_localize_labels_and_keep_svg_ids_unique_across_runs(self):
        metadata = {"lang": "en", "guide-author-profiles": {
            "kai-wu": {"github": "https://github.com/example", "email": "kai@example.edu"},
        }}
        source = '---\n' + json.dumps(metadata) + '\n---\n\n' + "\n\n".join(
            f'::: {{.contribution authors="{author}"}}\nText.\n:::'
            for author in ["kai-wu", "unknown", "kai-wu"])
        result = convert(source, "html5")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = ProfileMarkup(result.stdout)
        email_links = [link for link in parsed.elements("a", "guide-profile-link")
                       if link["attributes"]["data-profile-kind"] == "email"]
        self.assertEqual(len(email_links), 2)
        self.assertTrue(all(link["attributes"]["aria-label"] == "Kai Wu — Email: kai@example.edu"
                            for link in email_links))
        identifiers = [node["attributes"]["id"] for node in parsed.nodes if "id" in node["attributes"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        references = [match for node in parsed.nodes for attribute in node["attributes"].values()
                      for match in re.findall(r"url\(#([^)]+)\)", attribute or "")]
        self.assertTrue(references)
        self.assertTrue(set(references).issubset(identifiers))

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
