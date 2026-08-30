from __future__ import annotations

import math
import unittest

from pasko_agent_society.gate12.analysis import (
    alternate_cluster_contrast_from_counts,
    cross_gate_magnitude_consistency,
    exact_replication_statistics,
    hoeffding_interval,
    joint_classification,
    paired_mean_statistics,
    robustness_family_statistics,
)
from pasko_agent_society.gate12.registry import (
    ALL_ROBUSTNESS_CONTRAST_IDS,
    Gate12ProtocolError,
    T_CRITICAL_2999,
    T_CRITICAL_FAMILY_999,
)


class Gate12AnalysisTests(unittest.TestCase):
    def test_hand_checkable_mean_variance_and_interval(self) -> None:
        stats = paired_mean_statistics([-1.0, 0.0, 1.0], expected_units=3, t_critical=2.0)
        self.assertEqual(stats.estimate, 0.0)
        self.assertEqual(stats.sample_variance, 1.0)
        self.assertAlmostEqual(stats.standard_error, math.sqrt(1 / 3))
        self.assertAlmostEqual(stats.lower, -2 * math.sqrt(1 / 3))
        self.assertAlmostEqual(stats.upper, 2 * math.sqrt(1 / 3))

    def test_zero_variance_interval_collapses(self) -> None:
        stats = paired_mean_statistics([0.25] * 3, expected_units=3, t_critical=2.0)
        self.assertEqual(stats.sample_variance, 0.0)
        self.assertEqual(stats.lower, 0.25)
        self.assertEqual(stats.upper, 0.25)

    def test_exact_replication_uses_frozen_3000_pair_rule(self) -> None:
        result = exact_replication_statistics([0.01] * 3000)
        self.assertEqual(result["paired_difference"]["t_critical"], T_CRITICAL_2999)
        self.assertTrue(result["directional_support"])
        self.assertFalse(result["practical_magnitude"]["threshold_met"])
        self.assertFalse(result["hoeffding"]["certified_positive"])

    def test_primary_support_is_strictly_greater_than_zero(self) -> None:
        result = exact_replication_statistics([0.0] * 3000)
        self.assertFalse(result["directional_support"])
        self.assertEqual(result["paired_difference"]["lower"], 0.0)

    def test_hoeffding_width_matches_preregistered_formula(self) -> None:
        value = hoeffding_interval(0.0, 3000)
        self.assertAlmostEqual(value["half_width"], math.sqrt(2 * math.log(40) / 3000))

    def test_cross_gate_equivalence_labels_are_separate(self) -> None:
        consistent = cross_gate_magnitude_consistency(0.05, 0.001)
        self.assertEqual(
            consistent["classification"], "consistent within five percentage points"
        )
        inconsistent = cross_gate_magnitude_consistency(0.20, 0.001)
        self.assertEqual(
            inconsistent["classification"], "inconsistent by at least five percentage points"
        )
        inconclusive = cross_gate_magnitude_consistency(0.10, 0.02)
        self.assertEqual(inconclusive["classification"], "magnitude inconclusive")

    def test_alternate_topology_averages_three_with_one_cluster_contrast(self) -> None:
        self.assertAlmostEqual(
            alternate_cluster_contrast_from_counts(3, [6, 9, 12], denominator=18),
            0.33333333333333337,
        )
        with self.assertRaises(Gate12ProtocolError):
            alternate_cluster_contrast_from_counts(3, [6, 9], denominator=18)

    def test_robustness_family_requires_exactly_11_ordered_vectors(self) -> None:
        vectors = {cell_id: [0.2] * 1000 for cell_id in ALL_ROBUSTNESS_CONTRAST_IDS}
        result = robustness_family_statistics(vectors)
        self.assertEqual(result["family_size"], 11)
        self.assertEqual(len(result["cells"]), 11)
        self.assertEqual(
            result["cells"][0]["bonferroni_simultaneous_95"]["t_critical"],
            T_CRITICAL_FAMILY_999,
        )
        self.assertTrue(result["strong_robustness_certified"])
        with self.assertRaises(Gate12ProtocolError):
            robustness_family_statistics(dict(list(vectors.items())[:-1]))

    def test_one_nonpositive_lower_bound_prevents_strong_robustness(self) -> None:
        vectors = {cell_id: [0.2] * 1000 for cell_id in ALL_ROBUSTNESS_CONTRAST_IDS}
        values = [0.0] * 999 + [1.0]
        vectors[ALL_ROBUSTNESS_CONTRAST_IDS[-1]] = values
        result = robustness_family_statistics(vectors)
        self.assertFalse(result["strong_robustness_certified"])
        self.assertTrue(result["all_point_estimates_positive"])

    def test_strong_reversal_is_independent_modifier(self) -> None:
        vectors = {cell_id: [0.2] * 1000 for cell_id in ALL_ROBUSTNESS_CONTRAST_IDS}
        vectors[ALL_ROBUSTNESS_CONTRAST_IDS[3]] = [-0.2] * 1000
        result = robustness_family_statistics(vectors)
        self.assertTrue(result["strong_directional_reversal"])
        self.assertFalse(result["all_point_estimates_positive"])

    def test_nested_realizations_cannot_be_treated_as_3000_units(self) -> None:
        with self.assertRaises(Gate12ProtocolError):
            paired_mean_statistics([0.1] * 3000, expected_units=1000, t_critical=2.0)

    def test_all_frozen_joint_classifications_are_reachable(self) -> None:
        cases = [
            (
                "invalid/inconclusive",
                dict(campaigns_complete_and_valid=False, gate11_supported=True, replication_supported=True,
                     gate11_estimate=0.1, replication_estimate=0.1, robust_certified=True,
                     robust_all_positive=True, robust_reversal=False),
            ),
            (
                "replicated and robust",
                dict(campaigns_complete_and_valid=True, gate11_supported=True, replication_supported=True,
                     gate11_estimate=0.1, replication_estimate=0.1, robust_certified=True,
                     robust_all_positive=True, robust_reversal=False),
            ),
            (
                "replicated but specification-sensitive",
                dict(campaigns_complete_and_valid=True, gate11_supported=True, replication_supported=True,
                     gate11_estimate=0.1, replication_estimate=0.1, robust_certified=False,
                     robust_all_positive=False, robust_reversal=True),
            ),
            (
                "replicated; robustness directionally consistent but imprecise",
                dict(campaigns_complete_and_valid=True, gate11_supported=True, replication_supported=True,
                     gate11_estimate=0.1, replication_estimate=0.1, robust_certified=False,
                     robust_all_positive=True, robust_reversal=False),
            ),
            (
                "directionally consistent but imprecise",
                dict(campaigns_complete_and_valid=True, gate11_supported=True, replication_supported=False,
                     gate11_estimate=0.1, replication_estimate=0.01, robust_certified=False,
                     robust_all_positive=True, robust_reversal=False),
            ),
            (
                "failed replication",
                dict(campaigns_complete_and_valid=True, gate11_supported=True, replication_supported=False,
                     gate11_estimate=0.1, replication_estimate=0.0, robust_certified=False,
                     robust_all_positive=False, robust_reversal=False),
            ),
            (
                "heterogeneous/inconclusive",
                dict(campaigns_complete_and_valid=True, gate11_supported=False, replication_supported=True,
                     gate11_estimate=0.0, replication_estimate=0.1, robust_certified=False,
                     robust_all_positive=True, robust_reversal=False),
            ),
            (
                "concordant non-support",
                dict(campaigns_complete_and_valid=True, gate11_supported=False, replication_supported=False,
                     gate11_estimate=0.0, replication_estimate=-0.1, robust_certified=False,
                     robust_all_positive=False, robust_reversal=False),
            ),
        ]
        self.assertEqual(
            [joint_classification(**values)["classification"] for _, values in cases],
            [label for label, _ in cases],
        )
        self.assertTrue(joint_classification(**cases[2][1])["strong_directional_reversal_present"])

    def test_logically_impossible_flags_are_rejected(self) -> None:
        with self.assertRaises(Gate12ProtocolError):
            joint_classification(
                campaigns_complete_and_valid=True,
                gate11_supported=True,
                replication_supported=True,
                gate11_estimate=0.1,
                replication_estimate=0.1,
                robust_certified=True,
                robust_all_positive=False,
                robust_reversal=False,
            )


if __name__ == "__main__":
    unittest.main()
