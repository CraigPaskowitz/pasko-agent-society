from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from pasko_agent_society.gate11_manifest import implementation_source_hash as gate11_source_hash
from pasko_agent_society.gate12.manifest import (
    GATE11_EVIDENCE_INDEX_SHA256,
    GATE11_PASSPORT_SHA256,
    GATE11_PRIMARY_ANALYSIS_FILE_SHA256,
    GATE11_RESULT_REPORT_SHA256,
    implementation_source_hash,
    load_suite_spec,
    suite_spec_from_mapping,
)
from pasko_agent_society.gate12.registry import (
    GATE12_PREREGISTRATION_SHA256,
    Gate12ProtocolError,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "gate1_2_suite_v1.json"
PREREGISTRATION = ROOT / "preregistrations" / "GATE_1_2_PREREGISTRATION.md"


class Gate12ManifestTests(unittest.TestCase):
    def test_manifest_binds_all_frozen_campaign_counts(self) -> None:
        spec = load_suite_spec(MANIFEST)
        self.assertEqual(spec.raw["expected_artifacts"]["independent_units"], 14000)
        self.assertEqual(spec.raw["expected_artifacts"]["condition_runs"], 30000)
        self.assertEqual(spec.raw["expected_artifacts"]["pair_chunks"], 13000)
        self.assertEqual(spec.raw["expected_artifacts"]["cluster_chunks"], 1000)
        families = spec.raw["campaign_families"]
        self.assertEqual(families["exact_replication"]["root_seed"], 20260831)
        self.assertEqual(families["standard_robustness"]["root_seed"], 20260901)
        self.assertEqual(families["alternate_topology"]["root_seed"], 20260902)
        self.assertEqual(len(families["standard_robustness"]["cells"]), 10)

    def test_manifest_binds_exact_inference_and_classification(self) -> None:
        analysis = load_suite_spec(MANIFEST).raw["analysis"]
        self.assertEqual(
            analysis["primary_replication"]["t_critical_0_975"], "1.960755319205"
        )
        self.assertEqual(
            analysis["robustness_family"]["family_t_critical"], "2.844038318881"
        )
        self.assertEqual(analysis["robustness_family"]["family_size"], 11)
        self.assertEqual(len(analysis["joint_classification"]["ordered_labels"]), 8)

    def test_preregistration_bytes_remain_frozen(self) -> None:
        self.assertEqual(
            hashlib.sha256(PREREGISTRATION.read_bytes()).hexdigest(),
            GATE12_PREREGISTRATION_SHA256,
        )

    def test_gate11_source_and_public_result_hashes_are_unchanged(self) -> None:
        self.assertEqual(
            gate11_source_hash(),
            "c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09",
        )
        paths = {
            "GATE_1_1_RESULT_REPORT.md": GATE11_RESULT_REPORT_SHA256,
            "gate1_1_passport.json": GATE11_PASSPORT_SHA256,
            "evidence-index.json": GATE11_EVIDENCE_INDEX_SHA256,
            "primary-analysis.json": GATE11_PRIMARY_ANALYSIS_FILE_SHA256,
        }
        for name, expected in paths.items():
            value = hashlib.sha256((ROOT / "results" / "gate1_1" / name).read_bytes()).hexdigest()
            self.assertEqual(value, expected)

    def test_source_bundle_hash_is_stable_and_includes_shared_dependencies(self) -> None:
        first = implementation_source_hash(ROOT)
        second = implementation_source_hash(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        int(first, 16)
        self.assertNotEqual(first, gate11_source_hash())

    def test_unregistered_cell_or_parameter_mutation_is_rejected(self) -> None:
        spec = load_suite_spec(MANIFEST)
        changed = copy.deepcopy(spec.raw)
        changed["campaign_families"]["standard_robustness"]["cells"][0][
            "propagation_rounds"
        ] = 9
        with self.assertRaises(Gate12ProtocolError):
            suite_spec_from_mapping(changed)
        changed = copy.deepcopy(spec.raw)
        changed["campaign_families"]["standard_robustness"]["cells"].append(
            changed["campaign_families"]["standard_robustness"]["cells"][0]
        )
        with self.assertRaises(Gate12ProtocolError):
            suite_spec_from_mapping(changed)

    def test_external_or_host_path_is_rejected(self) -> None:
        spec = load_suite_spec(MANIFEST)
        changed = copy.deepcopy(spec.raw)
        changed["artifacts"]["root_directory"] = "/tmp/gate12"
        with self.assertRaises(Gate12ProtocolError):
            suite_spec_from_mapping(changed)

    def test_candidate_manifest_contains_no_outcome_or_authorization(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8").casefold()
        self.assertNotIn('"authorized": true', text)
        self.assertNotIn('"gate1_2_estimate"', text)
        self.assertNotIn('"treatment_result"', text)
        self.assertFalse((ROOT / "artifacts" / "gate1_2_v1").exists())
        self.assertFalse((ROOT / "results" / "gate1_2").exists())


if __name__ == "__main__":
    unittest.main()
