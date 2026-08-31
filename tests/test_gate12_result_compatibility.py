from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_gate12_result import (
    HISTORICAL_GATE2_ABSENCE_COMMITS,
    validate_historical_gate2_boundary,
    validate_result_package,
)


ROOT = Path(__file__).resolve().parents[1]


class Gate12ResultCompatibilityTests(unittest.TestCase):
    def canonical_validation_report(self):
        return json.loads((ROOT / "results/gate1_2/validation-report.json").read_text())

    def test_frozen_gate12_result_proves_gate2_had_not_started(self) -> None:
        validate_historical_gate2_boundary(self.canonical_validation_report())

    def test_same_frozen_evidence_validates_after_later_gate2_source_exists(self) -> None:
        self.assertTrue((ROOT / "pasko_agent_society/gate2/protocol.py").is_file())
        result = validate_result_package()
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["gate2_started"])

    def test_falsified_historical_boundary_is_rejected(self) -> None:
        falsified = copy.deepcopy(self.canonical_validation_report())
        falsified["package_boundary"]["gate2_started"] = True
        with self.assertRaisesRegex(ValueError, "historical boundary"):
            validate_historical_gate2_boundary(falsified)

    def test_gate2_path_in_any_frozen_tree_is_rejected(self) -> None:
        trees = {label: () for label in HISTORICAL_GATE2_ABSENCE_COMMITS}
        trees["gate1.2-implementation-freeze"] = ("pasko_agent_society/gate2/protocol.py",)
        with self.assertRaisesRegex(ValueError, "historical freeze tree"):
            validate_historical_gate2_boundary(self.canonical_validation_report(), trees)


if __name__ == "__main__":
    unittest.main()
