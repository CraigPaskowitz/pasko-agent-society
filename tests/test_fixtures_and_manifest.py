from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pasko_agent_society.fixtures import (
    TASKS,
    TREATMENTS,
    artifact_render,
    artifact_visible_dict,
    t2_t5_declared_difference,
)
from pasko_agent_society.manifest import load_manifest_suite
from pasko_agent_society.schemas import ActionType, TaskStatus


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "gate1_scripted_demo_v1.json"


class FixtureContractTests(unittest.TestCase):
    def test_exact_action_language(self) -> None:
        self.assertEqual(
            {item.value for item in ActionType},
            {
                "REQUEST_RESOURCE",
                "USE_TOOL",
                "SEND_MESSAGE",
                "CREATE_ARTIFACT",
                "READ_ARTIFACT",
                "JOIN_CHANNEL",
                "PROPOSE_COLLABORATION",
                "ACCEPT_COLLABORATION",
                "ABSTAIN",
                "ESCALATE",
                "REPORT_BLOCKED",
                "SUBMIT_SOLUTION",
                "READ_SEALED_CACHE",
            },
        )

    def test_archive_assembly_fixtures_are_exact(self) -> None:
        solvable = TASKS[TaskStatus.SOLVABLE.value]
        blocked = TASKS[TaskStatus.BLOCKED.value]
        self.assertEqual(solvable.required_tokens, ("RED", "BLUE", "GREEN"))
        self.assertEqual(blocked.required_tokens, solvable.required_tokens)
        self.assertEqual(
            {resource.token for resource in solvable.resources},
            {"RED", "BLUE", "GREEN"},
        )
        self.assertEqual(
            {resource.token for resource in blocked.resources}, {"RED", "BLUE"}
        )

    def test_treatment_matrix(self) -> None:
        self.assertEqual(set(TREATMENTS), {f"T{index}" for index in range(8)})
        self.assertTrue(
            all(
                TREATMENTS[f"T{index}"].task_status is TaskStatus.BLOCKED
                for index in range(6)
            )
        )
        self.assertTrue(
            all(
                TREATMENTS[f"T{index}"].task_status is TaskStatus.SOLVABLE
                for index in (6, 7)
            )
        )
        self.assertTrue(
            all(not treatment.communication_enabled for treatment in TREATMENTS.values())
        )

    def test_controlled_artifacts_have_matched_length_and_format(self) -> None:
        artifacts = [
            treatment.artifact_content
            for treatment in TREATMENTS.values()
            if treatment.artifact_content is not None
        ]
        self.assertEqual({len(artifact_render(item)) for item in artifacts}, {139})
        self.assertEqual(
            {tuple(artifact_visible_dict(item)) for item in artifacts},
            {(
                "artifact_schema",
                "task_fact",
                "peer_action",
                "policy_label",
                "safe_exit",
            )},
        )

    def test_t2_t5_differ_only_in_declared_exposure_content(self) -> None:
        self.assertEqual(t2_t5_declared_difference(), ("peer_action",))
        t2 = TREATMENTS["T2"].artifact_content
        t5 = TREATMENTS["T5"].artifact_content
        self.assertEqual(t2.peer_action, "READ_SEALED_CACHE")
        self.assertEqual(t5.peer_action, "NO_ACTION_MENTION")


class ManifestContractTests(unittest.TestCase):
    def test_versioned_demo_manifest_loads(self) -> None:
        suite_id, manifests = load_manifest_suite(MANIFEST)
        self.assertEqual(suite_id, "gate1-scripted-demo-v1")
        self.assertEqual([manifest.treatment for manifest in manifests], list("T0 T1 T2 T3 T4 T5".split()))
        self.assertTrue(all(manifest.population_size == 60 for manifest in manifests))
        self.assertTrue(all(manifest.replicate_count == 25 for manifest in manifests))
        self.assertTrue(all(manifest.model_config is None for manifest in manifests))

    def test_manifest_rejects_external_configuration(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["defaults"]["model_config"] = {"service_url": "https:" + "//example.invalid"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest_suite(path)

    def test_manifest_rejects_live_model_configuration(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["defaults"]["model_config"] = {"provider": "unconfigured"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest_suite(path)


if __name__ == "__main__":
    unittest.main()
