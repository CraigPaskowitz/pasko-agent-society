from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from pasko_agent_society.gate11_analysis import (
    AnalysisLockedError,
    analyze_primary_campaign,
    paired_statistics_from_counts,
)
from pasko_agent_society.gate11_protocol import T_CRITICAL_2999, primary_config
from pasko_agent_society.gate11_storage import (
    CampaignContext,
    CampaignPaths,
    add_content_hash,
)


class Gate11AnalysisTests(unittest.TestCase):
    def test_hand_checkable_paired_mean_variance_and_interval(self) -> None:
        ring = [0, 1, 2, 3]
        rewired = [1, 1, 4, 2]
        result = paired_statistics_from_counts(
            ring,
            rewired,
            denominator=4,
            t_critical=2.0,
        )
        # Pair differences are 0.25, 0, 0.5, -0.25.
        self.assertAlmostEqual(result["paired_difference"]["estimate"], 0.125)
        self.assertAlmostEqual(result["paired_difference"]["sample_variance"], 0.3125 / 3)
        expected_se = math.sqrt(0.3125 / 3) / 2
        self.assertAlmostEqual(result["paired_difference"]["standard_error"], expected_se)
        self.assertAlmostEqual(result["primary_interval"]["lower"], 0.125 - 2 * expected_se)
        self.assertAlmostEqual(result["primary_interval"]["upper"], 0.125 + 2 * expected_se)

    def test_zero_variance_interval_collapses_to_point_estimate(self) -> None:
        result = paired_statistics_from_counts(
            [0, 0, 0],
            [1, 1, 1],
            denominator=4,
            t_critical=2.0,
        )
        self.assertEqual(result["paired_difference"]["estimate"], 0.25)
        self.assertEqual(result["paired_difference"]["sample_variance"], 0.0)
        self.assertEqual(result["paired_difference"]["standard_error"], 0.0)
        self.assertEqual(result["primary_interval"]["lower"], 0.25)
        self.assertEqual(result["primary_interval"]["upper"], 0.25)

    def test_primary_direction_magnitude_and_hoeffding_outputs_are_distinct(self) -> None:
        result = paired_statistics_from_counts(
            [0] * 3000,
            [3] * 3000,
            denominator=54,
            t_critical=T_CRITICAL_2999,
        )
        self.assertTrue(result["directional_statistical_evidence"]["supported"])
        self.assertTrue(result["practical_magnitude"]["threshold_met"])
        self.assertTrue(
            result["distribution_free_conservative_certification"]["certified_positive"]
        )
        self.assertEqual(result["primary_interval"]["degrees_of_freedom"], 2999)
        self.assertEqual(result["primary_interval"]["t_critical"], 1.960755319205)
        self.assertAlmostEqual(
            result["distribution_free_conservative_certification"]["half_width"],
            math.sqrt(2 * math.log(40) / 3000),
        )

    def test_failure_to_support_does_not_assert_exact_zero(self) -> None:
        result = paired_statistics_from_counts(
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            denominator=4,
            t_critical=2.0,
        )
        self.assertFalse(result["directional_statistical_evidence"]["supported"])
        self.assertEqual(
            result["directional_statistical_evidence"]["rule"],
            "complete_valid_and_primary_lower_bound_strictly_greater_than_zero",
        )

    def _primary_context(self) -> CampaignContext:
        return CampaignContext(
            campaign_id="gate11-primary-3000-v1",
            campaign_spec_hash="sha256:" + "1" * 64,
            implementation_commit="1" * 40,
            implementation_source_hash="2" * 64,
            config=primary_config(),
        )

    def test_analysis_refuses_when_completion_manifest_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory) / "primary")
            with self.assertRaises(AnalysisLockedError):
                analyze_primary_campaign(self._primary_context(), paths)

    def test_analysis_refuses_forged_incomplete_completion_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory) / "primary")
            paths.root.mkdir(parents=True)
            forged = add_content_hash(
                {
                    "schema_version": "gate11-completion-manifest-v1",
                    "campaign_id": "gate11-primary-3000-v1",
                    "campaign_spec_hash": "sha256:" + "1" * 64,
                    "implementation_commit": "1" * 40,
                    "implementation_source_hash": "2" * 64,
                    "expected_pair_count": 3000,
                    "valid_pair_count": 2999,
                    "invalid_pair_count": 0,
                    "missing_pair_count": 1,
                    "duplicate_pair_count": 0,
                    "interrupted_temporary_file_count": 0,
                    "ordered_chunks": [],
                    "ordered_ensemble_hash": "sha256:" + "3" * 64,
                }
            )
            paths.completion_manifest.write_text(
                json.dumps(forged), encoding="utf-8"
            )
            with self.assertRaises(AnalysisLockedError):
                analyze_primary_campaign(self._primary_context(), paths)


if __name__ == "__main__":
    unittest.main()
