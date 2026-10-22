"""Keep the published bilingual addresses and discussion anchors after reorganization."""

from pathlib import Path
import json
import unittest

import yaml


BOOK = Path(__file__).resolve().parents[2] / "book"


class ReorganizationCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.aliases = yaml.safe_load((BOOK / "redirects.yml").read_text())["redirects"]

    def test_historical_addresses_have_same_language_english_mirrors(self):
        for old, new in self.aliases.items():
            if old.startswith("en/"):
                continue
            with self.subTest(old=old):
                self.assertEqual(self.aliases.get("en/" + old), "en/" + new)

    def test_imported_articles_keep_addresses_and_discussion_anchors_in_both_languages(self):
        manifest = json.loads((BOOK / "migration.json").read_text())
        for page in manifest["pages"]:
            current, discussion = page["path"], page["discussion_id"]
            for prefix in ("", "en/"):
                with self.subTest(page=current, language=prefix or "zh"):
                    if "previous_path" in page:
                        self.assertEqual(self.aliases[prefix + page["previous_path"]], prefix + current)
                    # Merged articles keep the retired discussion ID as a stable
                    # anchor even when the target uses another primary discussion.
                    self.assertIn("{#" + discussion + "}", (BOOK / prefix / current).read_text())
