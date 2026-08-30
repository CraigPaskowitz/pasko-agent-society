from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import pasko_agent_society.gate11_protocol as gate11_protocol
from pasko_agent_society.gate11_protocol import (
    GATE1_BASELINE_COMMIT,
    PREREGISTRATION_COMMIT,
    PREREGISTRATION_SHA256,
    PREREGISTRATION_TAG,
    ROOT_SEED,
    U64_SPACE,
    Gate11Config,
    Gate11InvariantError,
    condition_order,
    bounded_u64,
    fixture_config,
    graph_invariant_summary,
    primary_config,
    propagation_draw,
    rewire_ring,
    ring_edges,
    run_condition,
    run_pair,
    select_seed_agents,
    validate_pair_result,
)


class Gate11FrozenProtocolTests(unittest.TestCase):
    def test_primary_configuration_and_preregistration_identity_are_exact(self) -> None:
        config = primary_config()
        self.assertEqual(config, Gate11Config())
        self.assertEqual(config.root_seed, ROOT_SEED)
        self.assertEqual(config.pair_count, 3000)
        self.assertEqual(config.primary_denominator, 54)
        self.assertEqual(config.undirected_edge_count, 120)
        self.assertEqual(GATE1_BASELINE_COMMIT, "f4436dc0985620512b647d825e712c72accb3e7c")
        self.assertEqual(PREREGISTRATION_COMMIT, "cc1ab868a7401099751030580649e49258654fe2")
        self.assertEqual(PREREGISTRATION_TAG, "gate1.1-prereg-v1")
        self.assertEqual(
            PREREGISTRATION_SHA256,
            "e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706",
        )

    def test_fixture_seed_selection_is_deterministic_and_condition_matched(self) -> None:
        config = fixture_config(pair_count=1)
        pair_id = config.pair_id(0)
        first = select_seed_agents(config, pair_id)
        second = select_seed_agents(config, pair_id)
        self.assertEqual(first, second)
        self.assertEqual(len(first.seed_agents), config.seed_count)
        self.assertEqual(len(set(first.seed_agents)), config.seed_count)
        self.assertEqual(first.seed_agents, ("agent-000", "agent-002"))
        self.assertEqual(
            first.permutation_hash,
            "sha256:bdf5ca1d1e355541d220bd468a00543d69212a289fa68770f77bed149c3df8ee",
        )
        result = run_pair(config, pair_id)
        self.assertEqual(
            result["conditions"]["ring"]["seed_agents"],
            result["conditions"]["rewired"]["seed_agents"],
        )

    def test_fixture_rng_domains_are_separate_and_condition_blind(self) -> None:
        config = fixture_config(pair_count=1)
        pair_id = config.pair_id(0)
        source, recipient = config.agent_ids[:2]
        common = propagation_draw(config, pair_id, source, recipient)
        self.assertEqual(common, propagation_draw(config, pair_id, source, recipient))
        self.assertNotEqual(common, propagation_draw(config, pair_id, recipient, source))
        self.assertIn(condition_order(config, pair_id), {("ring", "rewired"), ("rewired", "ring")})
        self.assertEqual(common, 4802307515588513648)

    def test_bounded_u64_rejects_above_largest_multiple_before_modulo(self) -> None:
        with patch.object(
            gate11_protocol,
            "deterministic_u64",
            side_effect=[U64_SPACE - 1, 23],
        ) as mocked:
            draw = bounded_u64(7, ("fixture", "bounded"), 10)
        self.assertEqual(draw.value, 3)
        self.assertEqual(draw.raw_u64, 23)
        self.assertEqual(draw.rejection_counter, 1)
        self.assertEqual(mocked.call_args_list[0].args[-1], 0)
        self.assertEqual(mocked.call_args_list[1].args[-1], 1)

    def test_production_shape_ring_invariants_use_only_fixture_namespace(self) -> None:
        config = fixture_config(
            pair_count=1,
            population_size=60,
            seed_count=6,
            degree=4,
            accepted_swaps=0,
            rewire_attempt_cap=1,
            propagation_rounds=8,
        )
        summary = graph_invariant_summary(config, ring_edges(config))
        self.assertEqual(config.campaign_namespace, "fixture")
        self.assertEqual(summary["node_count"], 60)
        self.assertEqual(summary["edge_count"], 120)
        self.assertEqual(summary["degree_sequence"], [4] * 60)
        self.assertEqual(summary["connected_component_count"], 1)
        self.assertEqual(summary["self_loop_count"], 0)
        self.assertEqual(summary["duplicate_edge_count"], 0)

    def test_exactly_600_accepted_swaps_preserve_production_graph_shape(self) -> None:
        config = fixture_config(
            pair_count=1,
            population_size=60,
            seed_count=6,
            degree=4,
            accepted_swaps=600,
            rewire_attempt_cap=60_000,
            propagation_rounds=8,
        )
        first = rewire_ring(config, config.pair_id(0))
        second = rewire_ring(config, config.pair_id(0))
        self.assertEqual(first, second)
        self.assertEqual(first.accepted_swaps, 600)
        self.assertLessEqual(first.proposal_attempts, 60_000)
        self.assertEqual(len(first.accepted_attempt_indices), 600)
        self.assertEqual(first.invariant_summary["edge_count"], 120)
        self.assertEqual(first.invariant_summary["degree_sequence"], [4] * 60)
        self.assertEqual(first.invariant_summary["connected_component_count"], 1)

    def test_full_production_shape_integration_uses_only_fixture_identity(self) -> None:
        config = fixture_config(
            pair_count=1,
            population_size=60,
            seed_count=6,
            degree=4,
            accepted_swaps=600,
            rewire_attempt_cap=60_000,
            transmission_numerator=1,
            transmission_denominator=4,
            propagation_rounds=8,
        )
        result = run_pair(config, config.pair_id(0))
        self.assertEqual(result["campaign_namespace"], "fixture")
        self.assertEqual(result["pair_id"], "fixture-pair-0000")
        self.assertEqual(result["rewiring"]["accepted_swaps"], 600)
        self.assertEqual(set(result["conditions"]), {"ring", "rewired"})
        self.assertTrue(
            all(result["conditions"][name]["replay_verified"] for name in result["conditions"])
        )
        self.assertEqual(
            {
                result["conditions"][name]["metrics"]["primary_endpoint"]["denominator"]
                for name in result["conditions"]
            },
            {54},
        )

    def test_rewiring_hard_fails_instead_of_substituting_a_partial_graph(self) -> None:
        config = fixture_config(
            root_seed=1,
            pair_count=1,
            population_size=6,
            seed_count=1,
            degree=2,
            accepted_swaps=1,
            rewire_attempt_cap=1,
        )
        with self.assertRaisesRegex(Gate11InvariantError, "accepted-swap target"):
            rewire_ring(config, config.pair_id(0))

    def test_zero_probability_has_no_spontaneous_nonseed_adoption(self) -> None:
        config = fixture_config(pair_count=1, transmission_numerator=0)
        result = run_pair(config, config.pair_id(0))
        for condition in ("ring", "rewired"):
            endpoint = result["conditions"][condition]["metrics"]["primary_endpoint"]
            consequence = result["conditions"][condition]["metrics"]["boundary_attempt_consequence"]
            self.assertEqual(endpoint["adopted_unseeded_count"], 0)
            self.assertEqual(endpoint["denominator"], config.primary_denominator)
            self.assertEqual(consequence["unseeded_attempts"], 0)
            self.assertTrue(consequence["all_rejected"])

    def test_synchronous_round_prevents_new_adopter_forwarding_within_round(self) -> None:
        config = fixture_config(
            pair_count=1,
            population_size=6,
            seed_count=1,
            degree=2,
            accepted_swaps=0,
            rewire_attempt_cap=1,
            transmission_numerator=1,
            transmission_denominator=1,
            propagation_rounds=1,
        )
        pair_id = config.pair_id(0)
        result = run_condition(
            config,
            pair_id,
            "ring",
            ring_edges(config),
            select_seed_agents(config, pair_id),
        )
        self.assertEqual(result["metrics"]["primary_endpoint"]["adopted_unseeded_count"], 2)
        self.assertEqual({record["round"] for record in result["adoption_records"]}, {1})
        adopted_in_round = {record["agent_id"] for record in result["adoption_records"]}
        round_sources = {
            record["source_agent_id"] for record in result["opportunity_records"]
        }
        self.assertTrue(adopted_in_round.isdisjoint(round_sources))

    def test_multiple_successes_use_lexicographically_smallest_lineage_parent(self) -> None:
        config = fixture_config(
            pair_count=1,
            population_size=8,
            seed_count=4,
            degree=2,
            accepted_swaps=0,
            rewire_attempt_cap=1,
            transmission_numerator=1,
            transmission_denominator=1,
            propagation_rounds=1,
        )
        pair_id = config.pair_id(0)
        result = run_condition(
            config,
            pair_id,
            "ring",
            ring_edges(config),
            select_seed_agents(config, pair_id),
        )
        multiple = [
            record for record in result["adoption_records"] if len(record["successful_sources"]) > 1
        ]
        self.assertTrue(multiple)
        for record in multiple:
            choices = sorted(
                (item["source_agent_id"], item["message_id"])
                for item in record["successful_sources"]
            )
            primary = (
                record["primary_parent"]["source_agent_id"],
                record["primary_parent"]["message_id"],
            )
            self.assertEqual(primary, choices[0])

    def test_iteration_order_and_replay_do_not_change_fixture_result(self) -> None:
        config = fixture_config(pair_count=1)
        pair_id = config.pair_id(0)
        seeds = select_seed_agents(config, pair_id)
        edges = ring_edges(config)
        canonical = run_condition(config, pair_id, "ring", edges, seeds)
        reversed_order = run_condition(
            config,
            pair_id,
            "ring",
            tuple(reversed(edges)),
            seeds,
            _evaluation_order_for_test="reverse",
        )
        self.assertEqual(canonical["condition_hash"], reversed_order["condition_hash"])
        self.assertTrue(canonical["replay_verified"])

    def test_same_fixture_input_reproduces_pair_hash(self) -> None:
        config = fixture_config(pair_count=1)
        pair_id = config.pair_id(0)
        self.assertEqual(run_pair(config, pair_id)["pair_hash"], run_pair(config, pair_id)["pair_hash"])

    def test_impossible_topology_metadata_is_rejected(self) -> None:
        config = fixture_config(pair_count=1)
        result = run_pair(config, config.pair_id(0))
        corrupt = copy.deepcopy(result)
        corrupt["rewiring"]["invariant_summary"]["degree_sequence"][0] += 1
        with self.assertRaises(Gate11InvariantError):
            validate_pair_result(config, corrupt)


if __name__ == "__main__":
    unittest.main()
