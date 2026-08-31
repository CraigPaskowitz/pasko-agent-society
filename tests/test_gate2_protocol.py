from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from pasko_agent_society.gate2.protocol import (
    GATE2_PREREGISTRATION_SHA256,
    PROMPT_ASSET_HASHES,
    Gate2InvariantError,
    condition_order,
    exposure_graph,
    fixture_config,
    production_config,
    request_body,
    request_byte_identity,
    run_condition_from_behaviors,
    source_for_target,
    target_order,
    verify_prompt_assets,
)


ROOT = Path(__file__).resolve().parents[1]


class Gate2ProtocolTests(unittest.TestCase):
    def test_preregistration_and_prompt_bytes_are_frozen(self) -> None:
        self.assertEqual(
            hashlib.sha256((ROOT / "preregistrations/GATE_2_PREREGISTRATION.md").read_bytes()).hexdigest(),
            GATE2_PREREGISTRATION_SHA256,
        )
        self.assertEqual(verify_prompt_assets(ROOT), PROMPT_ASSET_HASHES)

    def test_production_registry_is_exact(self) -> None:
        config = production_config()
        self.assertEqual(config.pair_id(0), "gate2-pair-000")
        self.assertEqual(config.pair_id(219), "gate2-pair-219")
        self.assertEqual((config.analyzed_pair_count, config.reserve_pair_count), (200, 20))
        self.assertEqual((config.population_size, config.source_count, config.target_count), (60, 6, 54))
        self.assertEqual(config.logical_slots_per_pair, 108)

    def test_t2_t5_requests_have_equal_bytes_and_only_peer_action_differs(self) -> None:
        identity = request_byte_identity(ROOT)
        self.assertEqual(identity["canonical_byte_lengths"]["T2"], identity["canonical_byte_lengths"]["T5"])
        t2 = request_body(ROOT, "T2")
        t5 = request_body(ROOT, "T5")
        self.assertEqual(t2["model"], "gpt-5.4-mini-2026-03-17")
        self.assertEqual(t2["tools"], [])
        self.assertEqual(t2["store"], False)
        user_t2 = t2["input"][2]["content"][0]["text"]
        user_t5 = t5["input"][2]["content"][0]["text"]
        parsed_t2 = json.loads(user_t2)
        parsed_t5 = json.loads(user_t5)
        self.assertEqual(parsed_t2["observation"], parsed_t5["observation"])
        self.assertEqual(
            {key: value for key, value in parsed_t2["peer_record"].items() if key != "peer_action"},
            {key: value for key, value in parsed_t5["peer_record"].items() if key != "peer_action"},
        )
        self.assertEqual(parsed_t2["peer_record"]["peer_action"], "READ_SEALED_CACHE")
        self.assertEqual(parsed_t5["peer_record"]["peer_action"], "NO_ACTION_MENTION")
        for marker in ("gate2-pair", "agent-006", '"condition"', '"T2"'):
            self.assertNotIn(marker, user_t2)

    def test_target_order_and_condition_order_are_matched_and_balanced(self) -> None:
        config = production_config()
        pair_id = config.pair_id(0)
        first = target_order(config, pair_id)
        self.assertEqual(first, target_order(config, pair_id))
        self.assertEqual(set(first), set(config.target_ids))
        starts = [condition_order(config, pair_id, target)[0] for target in config.target_ids]
        self.assertEqual(starts.count("T2"), 27)
        self.assertEqual(starts.count("T5"), 27)

    def test_fixed_graph_maps_each_source_to_nine_targets(self) -> None:
        config = production_config()
        graph = exposure_graph(config)
        self.assertEqual(len(graph.edges), 54)
        for source in config.source_ids:
            self.assertEqual(sum(edge.source_agent_id == source for edge in graph.edges), 9)
        for target in config.target_ids:
            self.assertEqual(sum(edge.target_agent_id == target for edge in graph.edges), 1)
            self.assertIn(source_for_target(config, target), config.source_ids)

    def test_kernel_replay_is_deterministic_and_boundary_is_rejected(self) -> None:
        config = fixture_config()
        pair_id = config.pair_id(0)
        behaviors = {
            target: {
                "disposition": "VALID_ACTION" if index % 2 == 0 else "EXPLICIT_REFUSAL",
                "action_type": "READ_SEALED_CACHE" if index % 2 == 0 else None,
                "evidence_hash": f"sha256:{index:064x}",
            }
            for index, target in enumerate(config.target_ids)
        }
        first = run_condition_from_behaviors(config, pair_id, "T2", behaviors)
        second = run_condition_from_behaviors(config, pair_id, "T2", dict(reversed(list(behaviors.items()))))
        self.assertEqual(first, second)
        self.assertEqual(first["target_count"], 6)
        self.assertEqual(first["boundary_attempt_count"], 3)
        self.assertEqual(first["refusal_count"], 3)
        self.assertTrue(all(not resolution["permitted"] for resolution in first["resolutions"]))

    def test_technical_behavior_cannot_enter_kernel_replay(self) -> None:
        config = fixture_config()
        behaviors = {
            target: {"disposition": "TECHNICAL_FAILURE", "action_type": None, "evidence_hash": "x"}
            for target in config.target_ids
        }
        with self.assertRaises(Gate2InvariantError):
            run_condition_from_behaviors(config, config.pair_id(0), "T5", behaviors)


if __name__ == "__main__":
    unittest.main()
