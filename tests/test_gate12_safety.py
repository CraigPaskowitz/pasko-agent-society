from __future__ import annotations

import ast
import socket
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from pasko_agent_society.gate12.protocol import run_fixture_standard_pair
from pasko_agent_society.gate12.registry import fixture_standard_config


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "pasko_agent_society" / "gate12"


class Gate12SafetyTests(unittest.TestCase):
    def test_gate12_modules_have_no_external_io_or_dynamic_execution_imports(self) -> None:
        forbidden = {
            "asyncio.subprocess",
            "ftplib",
            "http",
            "importlib",
            "paramiko",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "telnetlib",
            "urllib",
            "webbrowser",
        }
        findings = []
        for path in sorted(PACKAGE.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if name in forbidden or name.split(".")[0] in forbidden:
                        findings.append((path.name, name))
        self.assertEqual(findings, [])

    def test_fixture_execution_never_calls_network_or_subprocess(self) -> None:
        config = fixture_standard_config(transmission_numerator=0, accepted_swaps=2)
        with patch.object(socket, "socket", side_effect=AssertionError("network called")), patch.object(
            subprocess, "Popen", side_effect=AssertionError("subprocess called")
        ):
            result = run_fixture_standard_pair(config, config.unit_id(0))
        self.assertEqual(result["conditions"]["ring"]["validity_status"], "VALID")

    def test_gate12_action_vocabulary_is_simulator_typed_and_bounded(self) -> None:
        source = (PACKAGE / "protocol.py").read_text(encoding="utf-8")
        self.assertIn("ActionType.READ_SEALED_CACHE", source)
        self.assertIn("ActionType.JOIN_CHANNEL", source)
        self.assertIn("ActionType.SEND_MESSAGE", source)
        self.assertIn("ActionType.REPORT_BLOCKED", source)
        for forbidden in ("os.system(", "eval(", "exec(", "subprocess.", "requests."):
            self.assertNotIn(forbidden, source)

    def test_no_llm_adapter_or_raw_gate12_production_artifact_exists(self) -> None:
        self.assertFalse((ROOT / "pasko_agent_society" / "gate12" / "llm_adapter.py").exists())
        self.assertFalse((ROOT / "artifacts" / "gate1_2_v1").exists())
        result = ROOT / "results" / "gate1_2"
        if result.exists():
            self.assertTrue((result / "evidence-index.json").exists())
            self.assertTrue((ROOT / "scripts" / "validate_gate12_result.py").exists())
            self.assertFalse(any(path.name == "chunks" for path in result.rglob("*")))

    def test_no_raw_production_seed_topology_or_chunk_fixture_is_tracked(self) -> None:
        tracked_names = [
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
        ]
        prohibited_prefixes = ("artifacts/gate1_2_v1/",)
        self.assertFalse(any(name.startswith(prohibited_prefixes) for name in tracked_names))
        self.assertFalse(any("/chunks/" in name for name in tracked_names))


if __name__ == "__main__":
    unittest.main()
