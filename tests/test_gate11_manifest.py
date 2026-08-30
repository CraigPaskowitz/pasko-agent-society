from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from pasko_agent_society.gate11_manifest import (
    campaign_spec_from_mapping,
    file_sha256,
    implementation_source_hash,
    load_campaign_spec,
)
from pasko_agent_society.gate11_protocol import (
    PREREGISTRATION_SHA256,
    Gate11ProtocolError,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "gate1_1_primary_v1.json"
PREREGISTRATION = ROOT / "preregistrations" / "GATE_1_1_PREREGISTRATION.md"


class Gate11CampaignSpecificationTests(unittest.TestCase):
    def test_campaign_specification_binds_every_frozen_primary_parameter(self) -> None:
        spec = load_campaign_spec(MANIFEST)
        self.assertEqual(spec.config.root_seed, 20260830)
        self.assertEqual(spec.config.pair_count, 3000)
        self.assertEqual(spec.config.population_size, 60)
        self.assertEqual(spec.config.seed_count, 6)
        self.assertEqual(spec.config.degree, 4)
        self.assertEqual(spec.config.accepted_swaps, 600)
        self.assertEqual(spec.config.rewire_attempt_cap, 60_000)
        self.assertEqual(spec.config.transmission_numerator, 1)
        self.assertEqual(spec.config.transmission_denominator, 4)
        self.assertEqual(spec.config.propagation_rounds, 8)
        self.assertEqual(spec.raw["mechanism"]["model_config"], None)
        self.assertEqual(spec.raw["expected_artifacts"]["pair_chunks"], 3000)
        self.assertEqual(spec.raw["expected_artifacts"]["condition_results"], 6000)

    def test_manifest_binds_the_certified_candidate_source_identity(self) -> None:
        spec = load_campaign_spec(MANIFEST, require_certified=True)
        self.assertEqual(spec.implementation_status, "CERTIFIED_CANDIDATE")
        self.assertEqual(
            spec.implementation_commit,
            "d31c78011abfc164fd3d20125bbe995e4023ee4a",
        )
        self.assertEqual(spec.implementation_source_hash, implementation_source_hash())

    def test_scientific_parameter_mutation_is_rejected(self) -> None:
        spec = load_campaign_spec(MANIFEST)
        changed = copy.deepcopy(spec.raw)
        changed["configuration"]["transmission_numerator"] = 2
        with self.assertRaises(Gate11ProtocolError):
            campaign_spec_from_mapping(changed)

    def test_external_or_host_path_configuration_is_rejected(self) -> None:
        spec = load_campaign_spec(MANIFEST)
        changed = copy.deepcopy(spec.raw)
        changed["artifacts"]["root_directory"] = "/tmp/gate11"
        with self.assertRaises(Gate11ProtocolError):
            campaign_spec_from_mapping(changed)

    def test_preregistration_bytes_remain_frozen(self) -> None:
        self.assertEqual(file_sha256(PREREGISTRATION), PREREGISTRATION_SHA256)

    def test_source_bundle_hash_is_stable_and_hex_encoded(self) -> None:
        first = implementation_source_hash()
        second = implementation_source_hash()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        int(first, 16)

    def test_manifest_contains_no_outcome_or_execution_authorization(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn('"authorized": true', text.casefold())
        self.assertNotIn('"delta_hat"', text.casefold())
        self.assertNotIn('"treatment_result"', text.casefold())
        self.assertFalse((ROOT / "artifacts" / "gate1_1_primary_v1").exists())
        self.assertEqual(
            hashlib.sha256(PREREGISTRATION.read_bytes()).hexdigest(),
            PREREGISTRATION_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
