from __future__ import annotations

import ast
import socket
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from pasko_agent_society.experiment import run_population
from pasko_agent_society.manifest import load_manifest_suite


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "pasko_agent_society"
MANIFEST = ROOT / "manifests" / "gate1_scripted_demo_v1.json"


class StaticSafetyTests(unittest.TestCase):
    def test_experiment_package_has_no_forbidden_import_dependency(self) -> None:
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

    def test_scripted_execution_does_not_call_network_or_subprocess(self) -> None:
        _, manifests = load_manifest_suite(MANIFEST)
        manifest = replace(manifests[0], population_size=3, replicate_count=1)
        with patch.object(socket, "socket", side_effect=AssertionError("network called")), patch.object(
            subprocess, "Popen", side_effect=AssertionError("subprocess called")
        ):
            result = run_population(manifest, 0)
        self.assertEqual(result.validity_status.value, "VALID")

    def test_project_has_no_runtime_dependencies(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", text)

    def test_no_llm_adapter_module_exists(self) -> None:
        self.assertFalse((PACKAGE / "llm_adapter.py").exists())

    def test_sealed_cache_enum_has_no_mapping_implementation(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(PACKAGE.glob("*.py"))
        )
        self.assertNotIn("sealed_cache_path", source.casefold())
        self.assertNotIn("sealed_cache_url", source.casefold())
        self.assertIn("Disallowed action reached an execution handler", source)


if __name__ == "__main__":
    unittest.main()
