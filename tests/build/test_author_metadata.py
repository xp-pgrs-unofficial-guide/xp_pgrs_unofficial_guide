"""Validate public academic profiles without querying or guessing anyone's identity."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts import build


class AuthorMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.book = Path(temporary.name)
        patcher = patch.object(build, "BOOK", self.book)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.metadata = {
            "guide-authors": {"example-author": "示例作者", "editorial": "编辑组"},
            "guide-authors-en": {"example-author": "Example Author", "editorial": "Editors"},
            "guide-author-profiles": {
                "example-author": {
                    "type": "person",
                    "affiliation": "示例机构", "affiliation-en": "Example institution",
                    "department": "示例院系", "department-en": "Example department",
                    "bio": "作者提供的公开简介。", "bio-en": "A public biography supplied by its author.",
                    "research-interests": ["研究方向"], "research-interests-en": ["Research area"],
                    "project-roles": ["编辑"], "project-roles-en": ["Editor"],
                    "orcid": "0000-0002-1694-233X",
                    "google-scholar": "https://scholar.google.com/citations?user=Example_ID&hl=en",
                    "website": "https://example.org/",
                    "github": "https://github.com/example-author",
                    "institutional-profile": "https://example.edu/people/example-author",
                },
                "editorial": {"type": "team"},
            },
        }

    def validate(self, metadata=None):
        metadata = self.metadata if metadata is None else metadata
        (self.book / "_authors.yml").write_text(yaml.safe_dump(metadata, allow_unicode=True), encoding="utf-8")
        return build.load_author_metadata()

    def test_complete_bilingual_academic_profiles_and_legacy_name_maps_are_supported(self):
        self.assertEqual(self.validate(), self.metadata)
        legacy = {"guide-authors": {"editorial": "Editors"}}
        self.assertEqual(self.validate(legacy), legacy)
        empty_profile = {**legacy, "guide-author-profiles": {"editorial": {}}}
        self.assertEqual(self.validate(empty_profile), empty_profile)

    def test_profile_ids_and_translated_name_ids_must_match_registered_authors(self):
        for field in ("guide-authors-en", "guide-author-profiles"):
            with self.subTest(field=field):
                changed = deepcopy(self.metadata)
                changed[field]["typo-author"] = "Typo" if field.endswith("-en") else {}
                with self.assertRaisesRegex(ValueError, "ID|已注册作者"):
                    self.validate(changed)

    def test_names_need_stable_ids_and_nonempty_display_strings(self):
        mutations = [
            {"guide-authors": {}},
            {"guide-authors": {"unstable ID": "Name"}},
            {"guide-authors": {"example-author": None}},
            {"guide-authors": {"example-author": " "}},
            {"guide-authors": {"example-author": "Multiple\nlines"}},
        ]
        for metadata in mutations:
            with self.subTest(metadata=metadata), self.assertRaisesRegex(ValueError, "guide-authors|ID|姓名"):
                self.validate(metadata)

    def test_duplicate_author_ids_or_profile_fields_cannot_be_silently_overwritten(self):
        for source in [
            "guide-authors:\n  example-author: First\n  example-author: Second\n",
            "guide-authors:\n  example-author: Name\nguide-author-profiles:\n  example-author:\n    type: person\n    type: team\n",
        ]:
            with self.subTest(source=source):
                (self.book / "_authors.yml").write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "重复键"):
                    build.load_author_metadata()

    def test_localized_profile_fields_are_paired_and_lists_keep_matching_items(self):
        for changes in [
            {"bio-en": None}, {"research-interests-en": "Not a list"},
            {"project-roles-en": ["Editor", "Reviewer"]}, {"affiliation": ""},
        ]:
            changed = deepcopy(self.metadata)
            changed["guide-author-profiles"]["example-author"].update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "非空|条目数"):
                self.validate(changed)
        changed = deepcopy(self.metadata)
        del changed["guide-author-profiles"]["example-author"]["bio-en"]
        with self.assertRaisesRegex(ValueError, "同时提供中英文"):
            self.validate(changed)

    def test_orcid_uses_canonical_digits_and_a_valid_checksum_including_final_x(self):
        for identifier in ["0000-0002-1825-0097", "0000-0002-1694-233X"]:
            self.metadata["guide-author-profiles"]["example-author"]["orcid"] = identifier
            self.validate()
        for identifier in ["0000-0002-1825-0098", "0000-0002-1694-233x", "https://orcid.org/0000-0002-1825-0097", 1234]:
            with self.subTest(identifier=identifier):
                self.metadata["guide-author-profiles"]["example-author"]["orcid"] = identifier
                with self.assertRaisesRegex(ValueError, "ORCID|校验位"):
                    self.validate()

    def test_links_must_be_safe_https_profile_urls(self):
        for address in ["javascript:alert(1)", "http://example.org", "//example.org", "https://user@example.org/",
                        "https://example.org:invalid/", "https://example.org/\nprofile", "https://example.org\\profile", ""]:
            with self.subTest(address=address):
                self.metadata["guide-author-profiles"]["example-author"]["website"] = address
                with self.assertRaisesRegex(ValueError, "HTTPS"):
                    self.validate()

    def test_scholar_and_github_links_point_to_profiles_rather_than_searches_or_repositories(self):
        mutations = [
            ("google-scholar", "https://scholar.google.com/scholar?q=Example"),
            ("google-scholar", "https://scholar.google.com/citations?user="),
            ("google-scholar", "https://scholar.google.com/citations?user=first&user=second"),
            ("google-scholar", "https://example.org/citations?user=Example"),
            ("github", "https://github.com/example/repository"),
        ]
        for field, address in mutations:
            changed = deepcopy(self.metadata)
            changed["guide-author-profiles"]["example-author"][field] = address
            with self.subTest(field=field, address=address), self.assertRaisesRegex(ValueError, "主页"):
                self.validate(changed)

    def test_team_and_placeholder_profiles_do_not_claim_individual_academic_ids(self):
        for kind in ("team", "placeholder"):
            with self.subTest(kind=kind):
                changed = deepcopy(self.metadata)
                changed["guide-author-profiles"]["example-author"]["type"] = kind
                with self.assertRaisesRegex(ValueError, "个人 ORCID"):
                    self.validate(changed)

    def test_misspelled_profile_fields_are_rejected_before_publication(self):
        self.metadata["guide-author-profiles"]["example-author"]["google-schollar"] = "https://example.org"
        with self.assertRaisesRegex(ValueError, "未知字段"):
            self.validate()

    def test_source_validation_checks_author_metadata_before_parsing_articles(self):
        self.metadata["guide-author-profiles"]["example-author"]["orcid"] = "0000-0002-1825-0098"
        (self.book / "_authors.yml").write_text(yaml.safe_dump(self.metadata), encoding="utf-8")
        (self.book / "_quarto.yml").write_text("book: {}\n", encoding="utf-8")
        with patch.dict("os.environ", {"GISCUS_REPO_ID": "", "GISCUS_CATEGORY_ID": "", "GISCUS_CATEGORY": ""}), \
                patch.object(build, "pandoc_json", side_effect=AssertionError("Must fail before parsing")):
            with self.assertRaisesRegex(ValueError, "校验位"):
                build.validate_sources("unused-quarto")


if __name__ == "__main__":
    unittest.main()
