"""Static safety regressions for workflow download support."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "server/routes/Workflows.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))


class WorkflowRoutesTests(unittest.TestCase):
    def test_all_endpoints_present(self):
        endpoints = set()
        for node in TREE.body:
            if isinstance(node, ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and decorator.args and isinstance(decorator.args[0], ast.Constant):
                        endpoints.add(decorator.args[0].value)
        self.assertTrue({
            "/civitai/workflows/settings",
            "/civitai/workflows/search",
            "/civitai/workflows/download",
        }.issubset(endpoints))

    def test_download_only_creates_exclusive_new_files(self):
        source = ast.get_source_segment(SOURCE.read_text(encoding="utf-8"), next(
            node for node in TREE.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "download_workflow"))
        self.assertIn('output.open("x"', source)
        self.assertNotIn('subprocess', source)

    def test_response_size_bounded(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("MAX_WORKFLOW_BYTES", source)
        self.assertIn("allow_redirects=False", source)


if __name__ == "__main__":
    unittest.main()
