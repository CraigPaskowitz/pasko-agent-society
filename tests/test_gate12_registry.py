from __future__ import annotations

import unittest
from dataclasses import replace

from pasko_agent_society.gate12.registry import (
    ALL_ROBUSTNESS_CONTRAST_IDS,
    ALTERNATE_TOPOLOGY_CELL_ID,
    ROBUSTNESS_CELL_IDS,
    Gate12ProtocolError,
    alternate_topology_config,
    exact_replication_config,
    fixture_standard_config,
    robustness_config,
    standard_config_mapping,
    validate_standard_config,
)


class Gate12FrozenRegistryTests(unittest.TestCase):
    def test_protocol_and_exact_replication_are_frozen(self) -> None:
        config = exact_replication_config()
        self.assertEqual(config.protocol_id, "PAS-GATE-1.2-ROBUSTNESS-V1")
        self.assertEqual(config.protocol_namespace, "gate12-v1")
        self.assertEqual(config.root_seed, 20260831)
        self.assertEqual(config.unit_count, 3000)
        self.assertEqual(config.population_size, 60)
        self.assertEqual(config.seed_count, 6)
        self.assertEqual(config.primary_denominator, 54)
        self.assertEqual(config.degree, 4)
        self.assertEqual(config.undirected_edge_count, 120)
        self.assertEqual(config.accepted_swaps, 600)
        self.assertEqual(config.rewire_attempt_cap, 60_000)
        self.assertEqual((config.transmission_numerator, config.transmission_denominator), (1, 4))
        self.assertEqual(config.propagation_rounds, 8)
        self.assertEqual(config.unit_id(0), "rep-pair-0000")
        self.assertEqual(config.unit_id(2999), "rep-pair-2999")

    def test_standard_cell_registry_is_exact_and_ordered(self) -> None:
        self.assertEqual(
            ROBUSTNESS_CELL_IDS,
            (
                "p-1-of-8",
                "p-3-of-8",
                "seeds-3",
                "seeds-12",
                "rounds-4",
                "rounds-12",
                "swaps-360",
                "swaps-840",
                "seed-placement-clustered",
                "seed-placement-dispersed",
            ),
        )
        self.assertEqual(
            ALL_ROBUSTNESS_CONTRAST_IDS,
            ROBUSTNESS_CELL_IDS + (ALTERNATE_TOPOLOGY_CELL_ID,),
        )
        self.assertEqual(len(ALL_ROBUSTNESS_CONTRAST_IDS), 11)

    def test_each_cell_changes_only_the_registered_parameter(self) -> None:
        anchor = standard_config_mapping(exact_replication_config())
        expected = {
            "p-1-of-8": ("transmission", {"numerator": 1, "denominator": 8}),
            "p-3-of-8": ("transmission", {"numerator": 3, "denominator": 8}),
            "seeds-3": ("seed_count", 3),
            "seeds-12": ("seed_count", 12),
            "rounds-4": ("propagation_rounds", 4),
            "rounds-12": ("propagation_rounds", 12),
            "swaps-360": ("accepted_swaps", 360),
            "swaps-840": ("accepted_swaps", 840),
            "seed-placement-clustered": ("seed_placement", "clustered"),
            "seed-placement-dispersed": ("seed_placement", "dispersed"),
        }
        ignored = {
            "campaign_id",
            "campaign_namespace",
            "cell_id",
            "root_seed",
            "unit_count",
            "expected_condition_runs",
        }
        for cell_id, (field, value) in expected.items():
            mapping = standard_config_mapping(robustness_config(cell_id))
            self.assertEqual(mapping[field], value)
            changed = {
                key
                for key in mapping
                if key not in ignored and mapping[key] != anchor[key]
            }
            if field == "seed_count":
                self.assertEqual(changed, {"seed_count", "primary_denominator"})
            else:
                self.assertEqual(changed, {field})

    def test_seed_count_denominators_are_exact(self) -> None:
        self.assertEqual(exact_replication_config().primary_denominator, 54)
        self.assertEqual(robustness_config("seeds-3").primary_denominator, 57)
        self.assertEqual(robustness_config("seeds-12").primary_denominator, 48)

    def test_alternate_topology_registry_is_exact(self) -> None:
        config = alternate_topology_config()
        self.assertEqual(config.root_seed, 20260902)
        self.assertEqual(config.unit_count, 1000)
        self.assertEqual(config.realization_count, 3)
        self.assertEqual(config.unit_id(0), "alt-cluster-0000")
        self.assertEqual(config.unit_id(999), "alt-cluster-0999")

    def test_unknown_or_mutated_production_cells_are_rejected(self) -> None:
        with self.assertRaises(Gate12ProtocolError):
            robustness_config("p-1-of-7")
        with self.assertRaises(Gate12ProtocolError):
            validate_standard_config(replace(robustness_config("rounds-4"), propagation_rounds=5))
        with self.assertRaises(Gate12ProtocolError):
            validate_standard_config(replace(exact_replication_config(), root_seed=1))

    def test_fixture_namespace_cannot_use_a_production_root(self) -> None:
        with self.assertRaises(Gate12ProtocolError):
            fixture_standard_config(root_seed=20260831)


if __name__ == "__main__":
    unittest.main()
