from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from pasko_agent_society.gate2.manifest import (
    EVIDENCE_SCHEMA_HASHES,
    implementation_source_hash,
    load_campaign_spec,
    verify_evidence_schema_files,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "pasko_agent_society" / "gate2"
MANIFEST = ROOT / "manifests" / "gate2_peer_exposure_v1.json"


class Gate2ManifestSafetyTests(unittest.TestCase):
    def test_candidate_manifest_binds_frozen_design_without_outcomes(self) -> None:
        spec = load_campaign_spec(MANIFEST)
        self.assertEqual(spec.implementation_status, "PENDING_CERTIFICATION")
        self.assertEqual(spec.raw["design"]["analyzed_matched_pairs"], 200)
        self.assertEqual(spec.raw["design"]["reserve_pair_ids"], [200, 219])
        self.assertEqual(spec.raw["expected"]["maximum_provider_attempts"], 71280)
        self.assertEqual(spec.raw["technical_validity"]["hard_provider_cost_ceiling_usd"], 85.0)
        self.assertIsNone(spec.raw["outcomes"])
        self.assertFalse(spec.raw["execution_authorized"])

    def test_source_bundle_identity_is_stable(self) -> None:
        first = implementation_source_hash(ROOT)
        second = implementation_source_hash(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        int(first, 16)

    def test_evidence_schema_bytes_are_frozen(self) -> None:
        self.assertEqual(verify_evidence_schema_files(ROOT), EVIDENCE_SCHEMA_HASHES)

    def test_deterministic_package_has_no_network_or_subprocess_import(self) -> None:
        forbidden = {"http", "requests", "socket", "subprocess", "urllib", "webbrowser"}
        findings = []
        for path in PACKAGE.glob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                findings.extend((path.name, name) for name in names if name.split(".")[0] in forbidden)
        self.assertEqual(findings, [])

    def test_live_transport_is_one_fixed_operator_boundary(self) -> None:
        source = (ROOT / "scripts/gate2_run.py").read_text()
        self.assertIn('RESPONSES_URL = "https://api.openai.com/v1/responses"', source)
        self.assertIn('INPUT_TOKENS_URL = "https://api.openai.com/v1/responses/input_tokens"', source)
        self.assertNotIn("request_body.get(\"url\")", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("eval(", source)
        self.assertNotIn("exec(", source)

    def test_no_production_artifact_or_api_key_is_tracked(self) -> None:
        self.assertFalse((ROOT / "artifacts/gate2_peer_exposure_v1").exists())
        for path in ROOT.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotRegex(text, r"sk-[A-Za-z0-9_-]{20,}")


if __name__ == "__main__":
    unittest.main()
