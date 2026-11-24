import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from agent_preflight import inspect,metadata

class AgentConfigTests(unittest.TestCase):
    def test_checkout(self):
        result=inspect(ROOT)
        self.assertEqual(result["errors"],[])
        self.assertIn("eps-resume",result["skills"])
        self.assertIn("eps-reviewer",result["agents"])
    def test_missing_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.md"
            path.write_text("no metadata",encoding="utf-8")
            with self.assertRaises(ValueError):
                metadata(path)
    def test_missing_required_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=inspect(Path(tmp))
            self.assertIn("Missing skill: eps-audit",result["errors"])
            self.assertIn("Missing agent: eps-engineer",result["errors"])
