from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pasko_agent_society.gate12.analysis import analyze_completed_suite
from pasko_agent_society.gate12.registry import (
    Gate12InvariantError,
    Gate12ProtocolError,
    exact_replication_config,
    fixture_alternate_config,
    fixture_standard_config,
)
from pasko_agent_society.gate12.storage import (
    CampaignIncompleteError,
    CampaignPaths,
    ChunkIntegrityError,
    SubcampaignContext,
    chunk_path,
    fixture_context,
    fixture_suite_contexts,
    load_unit_chunk,
    publish_completion_manifest,
    publish_suite_completion,
    publish_unit_chunk,
    rebuild_checkpoint,
    run_subcampaign,
    scan_campaign,
    verify_suite_completion,
)


class InjectedInterruption(RuntimeError):
    pass


class Gate12StorageTests(unittest.TestCase):
    @staticmethod
    def _paths(root: Path, name: str = "campaign") -> CampaignPaths:
        return CampaignPaths(root / name)

    @staticmethod
    def _raise_at(stage_name: str):
        def hook(stage: str) -> None:
            if stage == stage_name:
                raise InjectedInterruption(stage)

        return hook

    def _contexts(self):
        return (
            fixture_context(
                fixture_standard_config(
                    transmission_numerator=0,
                    accepted_swaps=2,
                    unit_count=2,
                )
            ),
            fixture_context(
                fixture_alternate_config(
                    transmission_numerator=0,
                    accepted_swaps=2,
                    unit_count=2,
                )
            ),
        )

    def test_pair_and_cluster_chunks_resume_without_duplicate_computation(self) -> None:
        for context in self._contexts():
            with self.subTest(kind=context.unit_kind), tempfile.TemporaryDirectory() as directory:
                paths = self._paths(Path(directory))
                unit_id = context.config.unit_id(0)
                calls = 0

                def computer(config, requested):
                    nonlocal calls
                    calls += 1
                    from pasko_agent_society.gate12.protocol import (
                        run_fixture_alternate_cluster,
                        run_fixture_standard_pair,
                    )

                    if context.unit_kind == "cluster":
                        return run_fixture_alternate_cluster(config, requested)
                    return run_fixture_standard_pair(config, requested)

                self.assertEqual(
                    publish_unit_chunk(context, paths, unit_id, computer=computer),
                    "newly_executed",
                )
                self.assertEqual(
                    publish_unit_chunk(context, paths, unit_id, computer=computer),
                    "resumed",
                )
                self.assertEqual(calls, 1)

    def test_per_unit_lock_prevents_duplicate_parallel_computation(self) -> None:
        context = self._contexts()[0]
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            unit_id = context.config.unit_id(0)
            calls = 0
            mutex = threading.Lock()

            def computer(config, requested):
                nonlocal calls
                from pasko_agent_society.gate12.protocol import run_fixture_standard_pair

                with mutex:
                    calls += 1
                return run_fixture_standard_pair(config, requested)

            with ThreadPoolExecutor(max_workers=4) as executor:
                statuses = list(
                    executor.map(
                        lambda _: publish_unit_chunk(
                            context,
                            paths,
                            unit_id,
                            computer=computer,
                            refresh_checkpoint=False,
                        ),
                        range(4),
                    )
                )
            self.assertEqual(calls, 1)
            self.assertEqual(statuses.count("newly_executed"), 1)
            self.assertEqual(statuses.count("resumed"), 3)

    def test_serial_parallel_and_worker_counts_are_identical(self) -> None:
        for context in self._contexts():
            with self.subTest(kind=context.unit_kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                serial_paths = self._paths(root, "serial")
                parallel_paths = self._paths(root, "parallel")
                serial = run_subcampaign(
                    context,
                    serial_paths,
                    worker_count=1,
                    invocation_id=f"fixture-{context.unit_kind}-serial",
                )
                parallel = run_subcampaign(
                    context,
                    parallel_paths,
                    worker_count=2,
                    invocation_id=f"fixture-{context.unit_kind}-parallel",
                )
                self.assertEqual(
                    scan_campaign(context, serial_paths).valid_chunk_hashes,
                    scan_campaign(context, parallel_paths).valid_chunk_hashes,
                )
                self.assertEqual(serial["checkpoint_hash"], parallel["checkpoint_hash"])

    def test_all_interruption_points_leave_recoverable_pair_and_cluster_state(self) -> None:
        stages = (
            "before-chunk-execution",
            "during-computation",
            "before-atomic-publication",
            "after-chunk-publication-before-checkpoint",
        )
        for context in self._contexts():
            for stage in stages:
                with self.subTest(kind=context.unit_kind, stage=stage), tempfile.TemporaryDirectory() as directory:
                    paths = self._paths(Path(directory))
                    unit_id = context.config.unit_id(0)
                    with self.assertRaises(InjectedInterruption):
                        publish_unit_chunk(
                            context,
                            paths,
                            unit_id,
                            failure_hook=self._raise_at(stage),
                        )
                    scan = scan_campaign(context, paths)
                    if stage == "after-chunk-publication-before-checkpoint":
                        self.assertEqual(scan.completed_count, 1)
                        self.assertFalse(paths.checkpoint.exists())
                        self.assertEqual(publish_unit_chunk(context, paths, unit_id), "resumed")
                    else:
                        self.assertEqual(scan.completed_count, 0)
                        self.assertIn(unit_id, scan.missing_unit_ids)

    def test_interrupted_checkpoint_reconstruction_preserves_prior_bytes(self) -> None:
        for context in self._contexts():
            with self.subTest(kind=context.unit_kind), tempfile.TemporaryDirectory() as directory:
                paths = self._paths(Path(directory))
                publish_unit_chunk(context, paths, context.config.unit_id(0))
                previous = paths.checkpoint.read_bytes()
                with self.assertRaises(InjectedInterruption):
                    rebuild_checkpoint(
                        context,
                        paths,
                        failure_hook=self._raise_at("during-checkpoint-reconstruction"),
                    )
                self.assertEqual(paths.checkpoint.read_bytes(), previous)

    def test_corrupt_checkpoint_and_chunk_are_preserved_and_rejected(self) -> None:
        context = self._contexts()[0]
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            unit_id = context.config.unit_id(0)
            publish_unit_chunk(context, paths, unit_id)
            checkpoint = json.loads(paths.checkpoint.read_text(encoding="utf-8"))
            checkpoint["content_hash"] = "sha256:" + "0" * 64
            paths.checkpoint.write_text(json.dumps(checkpoint), encoding="utf-8")
            corrupt_checkpoint = paths.checkpoint.read_bytes()
            with self.assertRaises(ChunkIntegrityError):
                rebuild_checkpoint(context, paths)
            self.assertEqual(paths.checkpoint.read_bytes(), corrupt_checkpoint)
            chunk = chunk_path(paths, unit_id)
            value = json.loads(chunk.read_text(encoding="utf-8"))
            value["content_hash"] = "sha256:" + "0" * 64
            chunk.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ChunkIntegrityError):
                load_unit_chunk(context, chunk, expected_unit_id=unit_id)

    def test_duplicate_and_partial_outputs_are_visible_but_not_credited(self) -> None:
        context = self._contexts()[0]
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            unit_id = context.config.unit_id(0)
            publish_unit_chunk(context, paths, unit_id)
            duplicate = paths.chunks / "duplicate.json"
            duplicate.write_bytes(chunk_path(paths, unit_id).read_bytes())
            scan = scan_campaign(context, paths)
            self.assertIn(unit_id, scan.duplicate_unit_ids)
            self.assertIn("duplicate.json", scan.invalid_files)
            duplicate.unlink()
            (paths.chunks / f".{context.config.unit_id(1)}.partial.tmp").write_text(
                "{", encoding="utf-8"
            )
            scan = scan_campaign(context, paths)
            self.assertEqual(len(scan.temporary_files), 1)
            self.assertEqual(scan.pending_count, 1)

    def test_mismatched_implementation_and_configuration_are_rejected(self) -> None:
        context = self._contexts()[0]
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            unit_id = context.config.unit_id(0)
            publish_unit_chunk(context, paths, unit_id)
            mismatch = SubcampaignContext(
                suite_id=context.suite_id,
                suite_spec_hash=context.suite_spec_hash,
                implementation_commit="different",
                implementation_source_hash=context.implementation_source_hash,
                config=context.config,
            )
            with self.assertRaises(ChunkIntegrityError):
                load_unit_chunk(mismatch, chunk_path(paths, unit_id), expected_unit_id=unit_id)

    def test_invalid_scientific_unit_remains_visible_and_blocks_completion(self) -> None:
        context = self._contexts()[0]
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))

            def invalid(_config, _unit_id):
                raise Gate12InvariantError("fixture invariant failure")

            publish_unit_chunk(context, paths, context.config.unit_id(0), computer=invalid)
            self.assertEqual(scan_campaign(context, paths).invalid_unit_ids, (context.config.unit_id(0),))
            with self.assertRaises(CampaignIncompleteError):
                publish_completion_manifest(context, paths)

    def test_pair_and_cluster_completion_manifests_verify_unique_units(self) -> None:
        for context in self._contexts():
            with self.subTest(kind=context.unit_kind), tempfile.TemporaryDirectory() as directory:
                paths = self._paths(Path(directory))
                run_subcampaign(
                    context,
                    paths,
                    worker_count=2,
                    invocation_id=f"fixture-{context.unit_kind}-complete",
                )
                completion = publish_completion_manifest(context, paths)
                self.assertEqual(completion["valid_unit_count"], 2)
                self.assertEqual(
                    [item["unit_id"] for item in completion["ordered_chunks"]],
                    list(context.expected_unit_ids),
                )

    def test_fixture_suite_completion_binds_pair_and_cluster_manifests(self) -> None:
        contexts = fixture_suite_contexts()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths_by_id = {}
            for context in contexts:
                paths = self._paths(root, context.unit_kind)
                paths_by_id[context.subcampaign_id] = paths
                run_subcampaign(
                    context,
                    paths,
                    worker_count=2,
                    invocation_id=f"fixture-suite-{context.unit_kind}",
                )
                publish_completion_manifest(context, paths)
            suite_path = root / "suite-completion-manifest.json"
            completion = publish_suite_completion(contexts, paths_by_id, suite_path)
            self.assertEqual(completion["independent_unit_count"], 4)
            self.assertEqual(completion["condition_run_count"], 12)
            self.assertEqual(
                verify_suite_completion(contexts, paths_by_id, suite_path), completion
            )

    def test_confirmatory_analysis_refuses_absent_suite_completion(self) -> None:
        contexts = fixture_suite_contexts()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths_by_id = {
                context.subcampaign_id: self._paths(root, context.unit_kind)
                for context in contexts
            }
            with self.assertRaises(CampaignIncompleteError):
                analyze_completed_suite(
                    contexts=contexts,
                    paths_by_id=paths_by_id,
                    suite_completion_path=root / "missing-suite-completion.json",
                    analysis_path=root / "analysis.json",
                )
            self.assertFalse((root / "analysis.json").exists())

    def test_production_runner_refuses_without_authorization_before_creating_artifacts(self) -> None:
        config = exact_replication_config()
        context = SubcampaignContext(
            suite_id="gate12-suite-v1",
            suite_spec_hash="sha256:" + "1" * 64,
            implementation_commit="1" * 40,
            implementation_source_hash="2" * 64,
            config=config,
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory), "production")
            with self.assertRaises(Gate12ProtocolError):
                run_subcampaign(
                    context,
                    paths,
                    worker_count=1,
                    invocation_id="unauthorized-production",
                )
            self.assertFalse(paths.root.exists())


if __name__ == "__main__":
    unittest.main()
