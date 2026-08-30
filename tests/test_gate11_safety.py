from __future__ import annotations

import ast
import socket
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from pasko_agent_society.gate11_protocol import fixture_config, run_pair


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "pasko_agent_society"


class Gate11SafetyBoundaryTests(unittest.TestCase):
    def test_gate11_fixture_execution_has_no_network_or_subprocess_call(self) -> None:
        config = fixture_config(pair_count=1, transmission_numerator=0)
        with patch.object(socket, "socket", side_effect=AssertionError("network called")), patch.object(
            subprocess, "Popen", side_effect=AssertionError("subprocess called")
        ):
            result = run_pair(config, config.pair_id(0))
        for condition in ("ring", "rewired"):
            self.assertTrue(result["conditions"][condition]["metrics"]["boundary_attempt_consequence"]["all_rejected"])

    def test_gate11_modules_import_no_external_io_or_dynamic_execution_capability(self) -> None:
        forbidden_imports = {
            "ftplib",
            "http",
            "importlib",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        forbidden_calls = {"eval", "exec", "compile", "__import__"}
        findings = []
        for path in sorted(PACKAGE.glob("gate11_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    names = []
                for name in names:
                    if name.split(".")[0] in forbidden_imports:
                        findings.append((path.name, name))
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in forbidden_calls
                ):
                    findings.append((path.name, node.func.id))
        self.assertEqual(findings, [])

    def test_no_llm_adapter_or_primary_outcome_artifact_exists(self) -> None:
        self.assertFalse((PACKAGE / "llm_adapter.py").exists())
        self.assertFalse((ROOT / "artifacts" / "gate1_1_primary_v1").exists())
        self.assertFalse((ROOT / "results" / "gate1_1_primary_analysis.json").exists())

    def test_gate11_action_vocabulary_remains_existing_typed_actions(self) -> None:
        source = (PACKAGE / "gate11_protocol.py").read_text(encoding="utf-8")
        self.assertIn("ActionType.READ_SEALED_CACHE", source)
        self.assertIn("ActionType.SEND_MESSAGE", source)
        self.assertIn("ActionType.REPORT_BLOCKED", source)


if __name__ == "__main__":
    unittest.main()
