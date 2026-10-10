"""Regression tests for live base-model enumeration; do not need a running ComfyUI."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "server/routes/GetBaseModels.py"
module = ast.parse(SOURCE.read_text(encoding="utf-8"))
function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "extract_base_models")
namespace = {}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), namespace)
extract = namespace["extract_base_models"]


class BaseModelEnumTests(unittest.TestCase):
    def test_includes_new_model_families(self):
        result = extract({"BaseModel": ["Anima", "ZImageTurbo", "Krea 2", "Anima"], "ActiveBaseModel": ["Anima"]})
        self.assertEqual(result, ["Anima", "Krea 2", "ZImageTurbo"])

    def test_does_not_use_active_only_list(self):
        with self.assertRaises(ValueError):
            extract({"ActiveBaseModel": ["Anima"]})

    def test_rejects_invalid_responses(self):
        for payload in (None, [], {}, {"BaseModel": []}, {"BaseModel": "SDXL"}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    extract(payload)

    def test_strips_non_string_values(self):
        self.assertEqual(extract({"BaseModel": [" Qwen ", 7, "", "SDXL 1.0"]}), ["Qwen", "SDXL 1.0"])


if __name__ == "__main__":
    unittest.main()
