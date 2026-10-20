"""Keep production links and Pages deployment tied to the main branch."""

import ast
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]


def allows_deployment(expression, ref, event):
    """Evaluate the workflow's small boolean guard without executing its text."""
    expression = expression.strip().removeprefix("${{").removesuffix("}}").strip()
    expression = expression.replace("github.ref", "ref").replace("github.event_name", "event")
    expression = expression.replace("&&", " and ").replace("||", " or ")
    context = {"ref": ref, "event": event}

    def value(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return context[node.id]
        if isinstance(node, ast.BoolOp):
            values = [value(part) for part in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            return value(node.left) == value(node.comparators[0])
        raise AssertionError("Unsupported Pages guard expression: " + ast.dump(node))

    return value(ast.parse(expression, mode="eval").body)


class ProductionPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = yaml.safe_load((ROOT / "book/_quarto.yml").read_text())
        cls.workflow = yaml.safe_load((ROOT / ".github/workflows/CI.yml").read_text())

    def test_article_source_links_use_main(self):
        self.assertEqual(self.config["book"]["repo-branch"], "main")

    def test_feature_branches_and_main_pull_requests_are_still_validated(self):
        # PyYAML's YAML 1.1 parser interprets the unquoted Actions key `on` as True.
        events = self.workflow.get("on", self.workflow.get(True))
        self.assertEqual(events["push"]["branches"], ["**"])
        self.assertEqual(events["pull_request"]["branches"], ["main"])
        self.assertIn("workflow_dispatch", events)

    def test_both_pages_gates_publish_only_main_pushes_and_manual_runs(self):
        build_steps = self.workflow["jobs"]["build"]["steps"]
        artifacts = [step for step in build_steps if step.get("uses", "").startswith("actions/upload-pages-artifact@")]
        self.assertEqual(len(artifacts), 1)
        guards = [artifacts[0]["if"], self.workflow["jobs"]["deploy"]["if"]]
        refs = ["refs/heads/main", "refs/heads/codex/quarto-guide", "refs/heads/codex/contribution-test",
                "refs/pull/42/merge", "refs/tags/v1.0.0"]
        events = ["push", "workflow_dispatch", "pull_request", "pull_request_target", "release"]
        for ref in refs:
            for event in events:
                expected = ref == "refs/heads/main" and event in {"push", "workflow_dispatch"}
                for guard in guards:
                    with self.subTest(ref=ref, event=event, guard=guard):
                        self.assertEqual(allows_deployment(guard, ref, event), expected)

    def test_deployment_waits_for_the_validated_build(self):
        jobs = self.workflow["jobs"]
        self.assertEqual(jobs["deploy"]["needs"], "build")
        self.assertEqual(jobs["deploy"]["environment"]["name"], "github-pages")
        self.assertNotIn("pages", jobs["build"].get("permissions", {}))
        self.assertEqual(jobs["deploy"]["permissions"]["pages"], "write")


if __name__ == "__main__":
    unittest.main()
