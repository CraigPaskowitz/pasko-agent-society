from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from pasko_agent_society.experiment import (
    assignment_for,
    replay_population,
    run_ensemble,
    run_population,
    summarize_ensemble,
)
from pasko_agent_society.manifest import load_manifest_suite
from pasko_agent_society.schemas import TaskStatus


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "gate1_scripted_demo_v1.json"


class ReproducibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_id, loaded = load_manifest_suite(MANIFEST)
        cls.manifests = tuple(
            replace(manifest, population_size=8, replicate_count=2)
            for manifest in loaded
        )

    def test_identical_manifest_and_seed_give_identical_hashes(self) -> None:
        first = run_population(self.manifests[2], 0)
        second = run_population(self.manifests[2], 0)
        self.assertEqual(first.result_hash, second.result_hash)
        self.assertEqual(first.passport.event_ledger_hash, second.passport.event_ledger_hash)
        self.assertEqual(first.passport.final_state_hash, second.passport.final_state_hash)
        self.assertEqual(first.passport.metrics_hash, second.passport.metrics_hash)

    def test_recorded_actions_replay_to_same_environment_hashes(self) -> None:
        result = run_population(self.manifests[2], 0)
        replay = replay_population(self.manifests[2], 0, result.actions)
        self.assertEqual(replay["event_ledger_hash"], result.passport.event_ledger_hash)
        self.assertEqual(replay["final_state_hash"], result.passport.final_state_hash)
        self.assertEqual(replay["actions_hash"], result.actions_hash)

    def test_paired_t2_t5_share_declared_randomness(self) -> None:
        t2 = run_population(self.manifests[2], 1)
        t5 = run_population(self.manifests[5], 1)
        self.assertEqual(t2.passport.assignment_hash, t5.passport.assignment_hash)
        self.assertEqual(t2.actions_hash, t5.actions_hash)
        self.assertNotEqual(t2.passport.event_ledger_hash, t5.passport.event_ledger_hash)

    def test_matched_assignments_reproduce(self) -> None:
        assignment = assignment_for(self.manifests[2], "replicate-000")
        self.assertEqual(
            assignment,
            assignment_for(self.manifests[2], "replicate-000"),
        )
        self.assertEqual(
            assignment,
            assignment_for(self.manifests[5], "replicate-000"),
        )

    def test_parallel_execution_preserves_ordered_results(self) -> None:
        sequential = run_ensemble(self.manifests, parallelism=1)
        parallel = run_ensemble(self.manifests, parallelism=3)
        self.assertEqual(
            [(item.treatment, item.replicate_id) for item in sequential],
            [(item.treatment, item.replicate_id) for item in parallel],
        )
        self.assertEqual(
            [item.result_hash for item in sequential],
            [item.result_hash for item in parallel],
        )

    def test_null_primary_result_renders_without_suppression(self) -> None:
        results = run_ensemble(self.manifests, parallelism=1)
        summary = summarize_ensemble(self.suite_id, results)
        self.assertEqual(summary["primary_estimand"]["estimand"], "T2_MINUS_T5")
        self.assertEqual(summary["primary_estimand"]["difference"], 0.0)
        self.assertFalse(summary["llm_behavior_evidence"])
        self.assertEqual(summary["population_runs"]["attempted"], 12)

    def test_passport_contains_required_hashes_and_runtime_metadata(self) -> None:
        passport = run_population(self.manifests[0], 0).passport
        for value in (
            passport.manifest_hash,
            passport.task_hash,
            passport.policy_hash,
            passport.graph_hash,
            passport.assignment_hash,
            passport.event_ledger_hash,
            passport.final_state_hash,
            passport.metrics_hash,
        ):
            self.assertTrue(value.startswith("sha256:"))
        self.assertEqual(passport.model_configuration, None)
        self.assertEqual(passport.model_call_provenance_hashes, ())
        self.assertFalse(passport.runtime_metadata["external_io_capability"])

    def test_solvable_t6_t7_plumbing_produces_compliant_solutions(self) -> None:
        base = self.manifests[0]
        for treatment in ("T6", "T7"):
            with self.subTest(treatment=treatment):
                manifest = replace(
                    base,
                    experiment_id=f"gate1-plumbing-{treatment.casefold()}",
                    treatment=treatment,
                    task_fixture=TaskStatus.SOLVABLE.value,
                    population_size=4,
                    replicate_count=1,
                )
                result = run_population(manifest, 0)
                self.assertTrue(all(outcome.solution_valid for outcome in result.outcomes))
                self.assertEqual(
                    result.metrics["first_boundary_attempt_incidence"]["numerator"], 0
                )
                self.assertEqual(
                    result.metrics["compliant_outcome_fraction"]["fraction"], 1.0
                )


if __name__ == "__main__":
    unittest.main()
