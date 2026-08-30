from __future__ import annotations

import copy
import unittest

from pasko_agent_society.gate11_protocol import graph_invariant_summary
from pasko_agent_society.gate12.protocol import (
    _topology_prefix,
    alternate_cluster_contrast,
    alternate_condition_order,
    propagation_draw,
    rewire_ring,
    run_fixture_alternate_cluster,
    run_fixture_standard_pair,
    select_seed_agents,
    standard_condition_order,
    standard_pair_contrast,
    validate_standard_pair_result,
)
from pasko_agent_society.gate12.registry import (
    Gate12InvariantError,
    Gate12ProtocolError,
    exact_replication_config,
    fixture_alternate_config,
    fixture_standard_config,
)


class Gate12ProtocolConformanceTests(unittest.TestCase):
    def test_production_execution_is_not_exposed_by_fixture_entrypoints(self) -> None:
        config = exact_replication_config()
        with self.assertRaises(Gate12ProtocolError):
            run_fixture_standard_pair(config, config.unit_id(0))

    def test_fixture_seed_selection_is_deterministic_and_matched(self) -> None:
        config = fixture_standard_config()
        unit_id = config.unit_id(0)
        first = select_seed_agents(config, unit_id)
        second = select_seed_agents(config, unit_id)
        pair = run_fixture_standard_pair(config, unit_id)
        self.assertEqual(first, second)
        self.assertEqual(pair["conditions"]["ring"]["seed_agents"], list(first.seed_agents))
        self.assertEqual(pair["conditions"]["rewired"]["seed_agents"], list(first.seed_agents))

    def test_rng_namespaces_are_cell_separated_and_gate11_disjoint(self) -> None:
        exact = exact_replication_config()
        self.assertEqual(
            exact.rng_prefix("rep-pair-0000"),
            ("gate12-v1", "exact-replication", "rep-pair-0000"),
        )
        fixture_a = fixture_standard_config(root_seed=7001, cell_id="fixture-a")
        fixture_b = fixture_standard_config(root_seed=7001, cell_id="fixture-b")
        unit_id = fixture_a.unit_id(0)
        draw_a = propagation_draw(fixture_a, unit_id, "agent-000", "agent-001")
        draw_b = propagation_draw(fixture_b, unit_id, "agent-000", "agent-001")
        self.assertNotEqual(draw_a, draw_b)
        self.assertNotEqual(fixture_a.protocol_namespace, "gate11-v1")
        self.assertNotEqual(exact.protocol_namespace, "gate11-v1")

    def test_condition_order_is_deterministic_but_canonical_storage_is_fixed(self) -> None:
        config = fixture_standard_config()
        unit_id = config.unit_id(0)
        self.assertEqual(standard_condition_order(config, unit_id), standard_condition_order(config, unit_id))
        pair = run_fixture_standard_pair(config, unit_id)
        self.assertEqual(list(pair["conditions"]), ["ring", "rewired"])

    def test_full_shape_360_600_840_swap_invariants_use_only_fixture_identity(self) -> None:
        for swaps in (360, 600, 840):
            config = fixture_standard_config(
                root_seed=771_000 + swaps,
                unit_count=1,
                population_size=60,
                seed_count=6,
                degree=4,
                accepted_swaps=swaps,
                rewire_attempt_cap=60_000,
                propagation_rounds=8,
            )
            result = rewire_ring(config, config.unit_id(0))
            summary = graph_invariant_summary(config, result.edges)
            self.assertEqual(result.accepted_swaps, swaps)
            self.assertLessEqual(result.proposal_attempts, 60_000)
            self.assertEqual(summary["edge_count"], 120)
            self.assertEqual(summary["degree_sequence"], [4] * 60)
            self.assertEqual(summary["connected_component_count"], 1)
            self.assertEqual(summary["self_loop_count"], 0)
            self.assertEqual(summary["duplicate_edge_count"], 0)

    def test_rewiring_hard_fails_without_partial_substitution(self) -> None:
        config = fixture_standard_config(
            root_seed=2,
            unit_count=1,
            population_size=6,
            seed_count=1,
            degree=2,
            accepted_swaps=1,
            rewire_attempt_cap=1,
        )
        with self.assertRaisesRegex(Gate12InvariantError, "accepted-swap target"):
            rewire_ring(config, config.unit_id(0))

    def test_impossible_rewiring_metadata_is_rejected(self) -> None:
        config = fixture_standard_config(accepted_swaps=2)
        result = run_fixture_standard_pair(config, config.unit_id(0))
        changed = copy.deepcopy(result)
        changed["rewiring"]["accepted_swaps"] = 1
        with self.assertRaises(Gate12InvariantError):
            validate_standard_pair_result(config, changed)

    def test_clustered_seed_placement_is_ring_coordinate_only(self) -> None:
        config = fixture_standard_config(
            root_seed=812_001,
            population_size=60,
            seed_count=6,
            degree=4,
            seed_placement="clustered",
        )
        seeds = select_seed_agents(config, config.unit_id(0)).seed_agents
        indices = sorted(int(seed.rsplit("-", 1)[1]) for seed in seeds)
        rotations = [sorted((start + offset) % 60 for offset in range(6)) for start in range(60)]
        self.assertIn(indices, rotations)

    def test_dispersed_seed_placement_is_exact_spacing_ten(self) -> None:
        config = fixture_standard_config(
            root_seed=812_002,
            population_size=60,
            seed_count=6,
            degree=4,
            seed_placement="dispersed",
        )
        seeds = select_seed_agents(config, config.unit_id(0)).seed_agents
        indices = sorted(int(seed.rsplit("-", 1)[1]) for seed in seeds)
        offset = indices[0]
        self.assertEqual(indices, [offset + 10 * index for index in range(6)])

    def test_seed_placement_does_not_consult_treatment_topology(self) -> None:
        config = fixture_standard_config(
            root_seed=812_003,
            population_size=60,
            seed_count=6,
            degree=4,
            seed_placement="clustered",
            accepted_swaps=20,
        )
        before = select_seed_agents(config, config.unit_id(0))
        rewire_ring(config, config.unit_id(0))
        after = select_seed_agents(config, config.unit_id(0))
        self.assertEqual(before, after)

    def test_synchronous_propagation_prevents_within_round_forwarding(self) -> None:
        config = fixture_standard_config(
            seed_count=1,
            transmission_numerator=1,
            transmission_denominator=1,
            accepted_swaps=2,
            propagation_rounds=3,
        )
        result = run_fixture_standard_pair(config, config.unit_id(0))
        for condition in result["conditions"].values():
            adoption_round = {
                record["agent_id"]: record["round"] for record in condition["adoption_records"]
            }
            seeds = set(condition["seed_agents"])
            for opportunity in condition["opportunity_records"]:
                source = opportunity["source_agent_id"]
                source_round = 0 if source in seeds else adoption_round[source]
                self.assertLess(source_round, opportunity["round"])

    def test_zero_probability_has_no_spontaneous_nonseed_adoption(self) -> None:
        config = fixture_standard_config(transmission_numerator=0, accepted_swaps=2)
        result = run_fixture_standard_pair(config, config.unit_id(0))
        for condition in result["conditions"].values():
            self.assertEqual(
                condition["metrics"]["primary_endpoint"]["adopted_unseeded_count"], 0
            )
            self.assertEqual(condition["adoption_records"], [])

    def test_each_adoption_has_one_rejected_boundary_consequence(self) -> None:
        config = fixture_standard_config(
            transmission_numerator=1,
            transmission_denominator=1,
            accepted_swaps=2,
        )
        result = run_fixture_standard_pair(config, config.unit_id(0))
        for condition in result["conditions"].values():
            endpoint = condition["metrics"]["primary_endpoint"]
            consequences = condition["metrics"]["boundary_attempt_consequence"]
            self.assertEqual(consequences["unseeded_attempts"], endpoint["adopted_unseeded_count"])
            self.assertTrue(consequences["all_rejected"])

    def test_iteration_order_does_not_change_fixture_result_hash(self) -> None:
        config = fixture_standard_config(accepted_swaps=2)
        unit_id = config.unit_id(0)
        canonical = run_fixture_standard_pair(config, unit_id)
        reversed_result = run_fixture_standard_pair(
            config, unit_id, _evaluation_order_for_test="reverse"
        )
        self.assertEqual(canonical["pair_hash"], reversed_result["pair_hash"])

    def test_fixture_replay_and_repeat_are_identical(self) -> None:
        config = fixture_standard_config(accepted_swaps=2)
        unit_id = config.unit_id(0)
        first = run_fixture_standard_pair(config, unit_id)
        second = run_fixture_standard_pair(config, unit_id)
        self.assertEqual(first["pair_hash"], second["pair_hash"])
        self.assertTrue(first["conditions"]["ring"]["replay_verified"])
        self.assertTrue(first["conditions"]["rewired"]["replay_verified"])

    def test_alternate_topology_uses_three_independent_rewiring_prefixes(self) -> None:
        config = fixture_alternate_config()
        unit_id = config.unit_id(0)
        prefixes = {
            _topology_prefix(config, unit_id, f"realization-{index}") for index in range(3)
        }
        self.assertEqual(len(prefixes), 3)
        self.assertEqual(len(alternate_condition_order(config, unit_id)), 4)

    def test_alternate_cluster_shares_seeds_and_common_propagation_draws(self) -> None:
        config = fixture_alternate_config(accepted_swaps=2)
        cluster = run_fixture_alternate_cluster(config, config.unit_id(0))
        seeds = {tuple(condition["seed_agents"]) for condition in cluster["conditions"].values()}
        self.assertEqual(len(seeds), 1)
        draw_maps = [
            {
                (item["source_agent_id"], item["recipient_agent_id"]): item["draw_u64"]
                for item in condition["opportunity_records"]
            }
            for condition in cluster["conditions"].values()
        ]
        for left_index, left in enumerate(draw_maps):
            for right in draw_maps[left_index + 1 :]:
                for key in set(left) & set(right):
                    self.assertEqual(left[key], right[key])

    def test_alternate_contrast_averages_three_before_subtracting_ring(self) -> None:
        config = fixture_alternate_config(
            transmission_numerator=1,
            transmission_denominator=1,
            accepted_swaps=2,
        )
        cluster = run_fixture_alternate_cluster(config, config.unit_id(0))
        ring = cluster["conditions"]["ring"]["metrics"]["primary_endpoint"]
        nested = [
            cluster["conditions"][f"realization-{index}"]["metrics"]["primary_endpoint"]
            for index in range(3)
        ]
        expected = sum(item["adopted_unseeded_count"] / item["denominator"] for item in nested) / 3
        expected -= ring["adopted_unseeded_count"] / ring["denominator"]
        self.assertAlmostEqual(alternate_cluster_contrast(cluster), expected)
        self.assertIsInstance(standard_pair_contrast(
            run_fixture_standard_pair(fixture_standard_config(accepted_swaps=2), "fixture-pair-0000")
        ), float)


if __name__ == "__main__":
    unittest.main()
