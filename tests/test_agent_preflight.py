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

    def test_invalid_rule_and_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rule=root/".agents/rules/bad.md"
            rule.parent.mkdir(parents=True)
            rule.write_text("---\ntrigger: modelDecision\n---\nBad rule\n",encoding="utf-8")
            agent=root/".agents/agents/bad/agent.md"
            agent.parent.mkdir(parents=True)
            agent.write_text("---\nname: bad\ndescription: test\ntools: [invented_tool]\nmainAgent: false\nsubagent: true\ncommandExecutionPolicy: sandbox\n---\nBad agent\n",encoding="utf-8")
            errors=inspect(root)["errors"]
            self.assertTrue(any("invalid rule trigger" in e for e in errors))
            self.assertTrue(any("tool outside" in e for e in errors))
