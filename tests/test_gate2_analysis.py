from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pasko_agent_society.gate2.analysis import paired_mean_statistics, analyze_completed_campaign
from pasko_agent_society.gate2.protocol import T_CRITICAL_199, fixture_config
from pasko_agent_society.gate2.storage import CampaignIncompleteError, CampaignPaths, fixture_context


class Gate2AnalysisTests(unittest.TestCase):
    def test_hand_checkable_paired_mean_rule_is_frozen(self) -> None:
        values = [0.1, -0.1] * 100
        result = paired_mean_statistics(values)
        self.assertAlmostEqual(result["estimate"], 0.0)
        self.assertEqual(result["degrees_of_freedom"], 199)
        self.assertEqual(result["t_critical"], T_CRITICAL_199)
        self.assertLess(result["lower"], 0)
        self.assertGreater(result["upper"], 0)

    def test_positive_zero_variance_fixture_clears_primary_rule(self) -> None:
        result = paired_mean_statistics([0.05] * 200)
        self.assertEqual(result["lower"], 0.05)
        self.assertEqual(result["upper"], 0.05)

    def test_analysis_lock_refuses_incomplete_fixture(self) -> None:
        context = fixture_context(fixture_config())
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            with self.assertRaises(CampaignIncompleteError):
                analyze_completed_campaign(context, paths)
            self.assertFalse(paths.primary_analysis.exists())


if __name__ == "__main__":
    unittest.main()
