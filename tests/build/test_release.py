"""Exercise the actual release workflow scripts without contacting GitHub."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/release_on_tag.yml").read_text())
STEPS = {step["name"]: step for step in WORKFLOW["jobs"]["release"]["steps"]}


class BilingualReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.env = os.environ.copy()
        # Never pass a developer's authentication tokens to the stub CLI.
        for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
            self.env.pop(name, None)
        self.env.update({
            "REQUESTED_TAG": "", "REF_TYPE": "tag", "REF_NAME": "v1.1.0",
            "GITHUB_OUTPUT": str(self.root / "outputs"),
            "ASSET_ZH": "xp_pgrs_unofficial_guide_1.1.0.pdf",
            "ASSET_EN": "xp_pgrs_unofficial_guide_1.1.0_en.pdf",
            "RELEASE_TAG": "v1.1.0",
        })

    def run_step(self, name):
        return subprocess.run(["bash", "-c", STEPS[name]["run"]], cwd=self.root,
                              env=self.env, text=True, capture_output=True)

    def init_repository(self):
        for args in (["init", "--quiet"],
                     ["-c", "user.name=Release test", "-c", "user.email=release@example.invalid",
                      "commit", "--allow-empty", "--quiet", "-m", "Fixture"],
                     ["tag", "v1.1.0"]):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def test_tag_push_produces_both_versioned_asset_names(self):
        self.init_repository()
        result = self.run_step("Resolve existing release tag")
        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = dict(line.split("=", 1) for line in (self.root / "outputs").read_text().splitlines())
        self.assertEqual(outputs, {"tag": "v1.1.0", "asset_zh": self.env["ASSET_ZH"],
                                   "asset_en": self.env["ASSET_EN"]})

    def test_manual_run_uses_requested_existing_tag(self):
        self.init_repository()
        self.env.update(REQUESTED_TAG="v1.1.0", REF_TYPE="branch", REF_NAME="main")
        result = self.run_step("Resolve existing release tag")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tag=v1.1.0\n", (self.root / "outputs").read_text())

    def test_manual_run_cannot_guess_or_create_a_tag(self):
        self.init_repository()
        for requested in ("", "v9.9.9"):
            with self.subTest(requested=requested):
                self.env.update(REQUESTED_TAG=requested, REF_TYPE="branch", REF_NAME="main")
                self.assertNotEqual(self.run_step("Resolve existing release tag").returncode, 0)
                self.assertFalse((self.root / "outputs").exists())

    def write_sources(self):
        files = [self.root / "book/_book/xp-pgrs-unofficial-guide.pdf",
                 self.root / "book/_book/en/xp-pgrs-unofficial-guide.pdf"]
        for file, content in zip(files, (b"%PDF-Chinese fixture", b"%PDF-English fixture")):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)
        return files

    def test_prepare_copies_the_correct_language_to_each_asset(self):
        sources = self.write_sources()
        result = self.run_step("Prepare versioned PDFs")
        self.assertEqual(result.returncode, 0, result.stderr)
        for source, variable in zip(sources, ("ASSET_ZH", "ASSET_EN")):
            self.assertEqual((self.root / self.env[variable]).read_bytes(), source.read_bytes())

    def test_prepare_rejects_either_missing_or_empty_pdf(self):
        for index in (0, 1):
            for missing in (True, False):
                with self.subTest(language=index, missing=missing):
                    sources = self.write_sources()
                    if missing:
                        sources[index].unlink()
                    else:
                        sources[index].write_bytes(b"")
                    result = self.run_step("Prepare versioned PDFs")
                    self.assertNotEqual(result.returncode, 0)
                    for variable in ("ASSET_ZH", "ASSET_EN"):
                        self.assertFalse((self.root / self.env[variable]).exists())

    def install_gh_stub(self, exists):
        folder = self.root / "bin"
        folder.mkdir(exist_ok=True)
        stub = folder / "gh"
        stub.write_text("""#!/usr/bin/env python3
import json, os, sys
with open(os.environ['GH_TEST_CALLS'], 'a') as output:
    output.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1:3] == ['release', 'view']:
    sys.exit(0 if os.environ['GH_TEST_EXISTS'] == '1' else 1)
""")
        stub.chmod(0o755)
        self.env.update(PATH=str(folder) + os.pathsep + os.environ["PATH"],
                        GH_TEST_CALLS=str(self.root / "gh-calls.jsonl"),
                        GH_TEST_EXISTS="1" if exists else "0")

    def check_publish(self, exists):
        self.install_gh_stub(exists)
        result = self.run_step("Publish PDF release")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in (self.root / "gh-calls.jsonl").read_text().splitlines()]
        self.assertEqual(calls[0], ["release", "view", "v1.1.0"])
        action = "upload" if exists else "create"
        expected = ["release", action, "v1.1.0", self.env["ASSET_ZH"], self.env["ASSET_EN"]]
        expected += ["--clobber"] if exists else ["--verify-tag", "--title", "v1.1.0", "--generate-notes"]
        self.assertEqual(calls[1:], [expected])

    def test_new_release_uploads_both_pdfs(self):
        self.check_publish(exists=False)

    def test_existing_release_replaces_both_pdfs(self):
        self.check_publish(exists=True)


if __name__ == "__main__":
    unittest.main()
