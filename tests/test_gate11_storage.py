from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pasko_agent_society.gate11_protocol import (
    Gate11InvariantError,
    Gate11ProtocolError,
    fixture_config,
    primary_config,
    run_pair,
)
from pasko_agent_society.gate11_storage import (
    CampaignContext,
    CampaignIncompleteError,
    CampaignPaths,
    ChunkIntegrityError,
    fixture_context,
    load_pair_chunk,
    publish_completion_manifest,
    publish_pair_chunk,
    rebuild_checkpoint,
    run_campaign,
    scan_campaign,
)


class InjectedInterruption(RuntimeError):
    pass


class Gate11StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = fixture_config(
            pair_count=2,
            transmission_numerator=0,
            accepted_swaps=3,
        )
        self.context = fixture_context(self.config)

    def _paths(self, root: Path, name: str = "campaign") -> CampaignPaths:
        return CampaignPaths(root / name)

    @staticmethod
    def _raise_at(stage_name: str):
        def hook(stage: str) -> None:
            if stage == stage_name:
                raise InjectedInterruption(stage)

        return hook

    def test_same_fixture_chunk_is_resumed_without_duplicate_computation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            calls = 0

            def computer(config, requested_pair):
                nonlocal calls
                calls += 1
                return run_pair(config, requested_pair)

            first = publish_pair_chunk(self.context, paths, pair_id, computer=computer)
            second = publish_pair_chunk(self.context, paths, pair_id, computer=computer)
            self.assertEqual(first, "newly_executed")
            self.assertEqual(second, "resumed")
            self.assertEqual(calls, 1)
            self.assertEqual(scan_campaign(self.context, paths).completed_count, 1)

    def test_concurrent_workers_compute_one_pair_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            calls = 0
            mutex = threading.Lock()

            def computer(config, requested_pair):
                nonlocal calls
                with mutex:
                    calls += 1
                return run_pair(config, requested_pair)

            with ThreadPoolExecutor(max_workers=4) as executor:
                statuses = list(
                    executor.map(
                        lambda _: publish_pair_chunk(
                            self.context,
                            paths,
                            pair_id,
                            computer=computer,
                            refresh_checkpoint=False,
                        ),
                        range(4),
                    )
                )
            self.assertEqual(calls, 1)
            self.assertEqual(statuses.count("newly_executed"), 1)
            self.assertEqual(statuses.count("resumed"), 3)

    def test_serial_and_parallel_fixture_campaigns_have_identical_ordered_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            serial_paths = self._paths(root, "serial")
            parallel_paths = self._paths(root, "parallel")
            serial = run_campaign(
                self.context,
                serial_paths,
                worker_count=1,
                invocation_id="fixture-serial",
            )
            parallel = run_campaign(
                self.context,
                parallel_paths,
                worker_count=2,
                invocation_id="fixture-parallel",
            )
            serial_scan = scan_campaign(self.context, serial_paths)
            parallel_scan = scan_campaign(self.context, parallel_paths)
            self.assertEqual(serial_scan.valid_chunk_hashes, parallel_scan.valid_chunk_hashes)
            self.assertEqual(serial["completed"], 2)
            self.assertEqual(parallel["completed"], 2)
            self.assertEqual(serial["checkpoint_hash"], parallel["checkpoint_hash"])

    def test_interruption_before_execution_leaves_no_credited_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            with self.assertRaises(InjectedInterruption):
                publish_pair_chunk(
                    self.context,
                    paths,
                    pair_id,
                    failure_hook=self._raise_at("before-chunk-execution"),
                )
            scan = scan_campaign(self.context, paths)
            self.assertEqual(scan.completed_count, 0)
            self.assertIn(pair_id, scan.missing_pair_ids)

    def test_interruption_during_computation_leaves_no_credited_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            with self.assertRaises(InjectedInterruption):
                publish_pair_chunk(
                    self.context,
                    paths,
                    pair_id,
                    failure_hook=self._raise_at("during-computation"),
                )
            self.assertEqual(scan_campaign(self.context, paths).completed_count, 0)

    def test_interruption_before_atomic_publication_preserves_only_a_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            with self.assertRaises(InjectedInterruption):
                publish_pair_chunk(
                    self.context,
                    paths,
                    pair_id,
                    failure_hook=self._raise_at("before-atomic-publication"),
                )
            scan = scan_campaign(self.context, paths)
            self.assertEqual(scan.completed_count, 0)
            self.assertEqual(len(scan.temporary_files), 1)

    def test_restart_after_chunk_publication_reconstructs_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            with self.assertRaises(InjectedInterruption):
                publish_pair_chunk(
                    self.context,
                    paths,
                    pair_id,
                    failure_hook=self._raise_at("after-chunk-publication-before-checkpoint"),
                )
            self.assertTrue((paths.chunks / f"{pair_id}.json").exists())
            self.assertFalse(paths.checkpoint.exists())
            self.assertEqual(publish_pair_chunk(self.context, paths, pair_id), "resumed")
            self.assertTrue(paths.checkpoint.exists())
            self.assertEqual(scan_campaign(self.context, paths).completed_count, 1)

    def test_interrupted_checkpoint_reconstruction_keeps_previous_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            publish_pair_chunk(self.context, paths, self.config.pair_id(0))
            previous = paths.checkpoint.read_bytes()
            with self.assertRaises(InjectedInterruption):
                rebuild_checkpoint(
                    self.context,
                    paths,
                    failure_hook=self._raise_at("during-checkpoint-reconstruction"),
                )
            self.assertEqual(paths.checkpoint.read_bytes(), previous)

    def test_corrupt_checkpoint_is_preserved_and_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            publish_pair_chunk(self.context, paths, self.config.pair_id(0))
            checkpoint = json.loads(paths.checkpoint.read_text(encoding="utf-8"))
            checkpoint["content_hash"] = "sha256:" + "0" * 64
            paths.checkpoint.write_text(json.dumps(checkpoint), encoding="utf-8")
            corrupt_bytes = paths.checkpoint.read_bytes()
            with self.assertRaises(ChunkIntegrityError):
                rebuild_checkpoint(self.context, paths)
            self.assertEqual(paths.checkpoint.read_bytes(), corrupt_bytes)

    def test_corrupted_malformed_and_duplicate_chunks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            publish_pair_chunk(self.context, paths, pair_id)
            final = paths.chunks / f"{pair_id}.json"
            duplicate = paths.chunks / "duplicate.json"
            duplicate.write_bytes(final.read_bytes())
            scan = scan_campaign(self.context, paths)
            self.assertIn("duplicate.json", scan.invalid_files)
            self.assertIn(pair_id, scan.duplicate_pair_ids)
            duplicate.unlink()
            data = json.loads(final.read_text(encoding="utf-8"))
            data["content_hash"] = "sha256:" + "0" * 64
            final.write_text(json.dumps(data), encoding="utf-8")
            self.assertIn(final.name, scan_campaign(self.context, paths).invalid_files)
            with self.assertRaises(ChunkIntegrityError):
                load_pair_chunk(self.context, final, expected_pair_id=pair_id)

    def test_partial_outputs_are_visible_but_never_credited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            paths.chunks.mkdir(parents=True)
            (paths.chunks / ".fixture-pair-0000.partial.tmp").write_text("{", encoding="utf-8")
            scan = scan_campaign(self.context, paths)
            self.assertEqual(scan.completed_count, 0)
            self.assertEqual(len(scan.temporary_files), 1)
            self.assertEqual(scan.pending_count, 2)

    def test_mismatched_configuration_and_implementation_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            pair_id = self.config.pair_id(0)
            publish_pair_chunk(self.context, paths, pair_id)
            mismatched = CampaignContext(
                campaign_id=self.context.campaign_id,
                campaign_spec_hash=self.context.campaign_spec_hash,
                implementation_commit="different-fixture-implementation",
                implementation_source_hash=self.context.implementation_source_hash,
                config=self.config,
            )
            with self.assertRaises(ChunkIntegrityError):
                load_pair_chunk(
                    mismatched,
                    paths.chunks / f"{pair_id}.json",
                    expected_pair_id=pair_id,
                )

    def test_invalid_completed_chunk_remains_visible_and_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))

            def invalid_computer(_config, _pair_id):
                raise Gate11InvariantError("fixture invariant failure")

            publish_pair_chunk(
                self.context,
                paths,
                self.config.pair_id(0),
                computer=invalid_computer,
            )
            scan = scan_campaign(self.context, paths)
            self.assertEqual(scan.invalid_pair_ids, (self.config.pair_id(0),))
            with self.assertRaises(CampaignIncompleteError):
                publish_completion_manifest(self.context, paths)

    def test_missing_pair_blocks_completion_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            publish_pair_chunk(self.context, paths, self.config.pair_id(0))
            with self.assertRaises(CampaignIncompleteError):
                publish_completion_manifest(self.context, paths)

    def test_fixture_completion_manifest_verifies_exact_unique_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            run_campaign(
                self.context,
                paths,
                worker_count=2,
                invocation_id="fixture-complete",
            )
            completion = publish_completion_manifest(self.context, paths)
            self.assertEqual(completion["valid_pair_count"], 2)
            self.assertEqual(completion["missing_pair_count"], 0)
            self.assertEqual(
                [item["pair_id"] for item in completion["ordered_chunks"]],
                [self.config.pair_id(0), self.config.pair_id(1)],
            )

    def test_primary_campaign_cannot_start_without_separate_authorization(self) -> None:
        context = CampaignContext(
            campaign_id="gate11-primary-3000-v1",
            campaign_spec_hash="sha256:" + "1" * 64,
            implementation_commit="1" * 40,
            implementation_source_hash="2" * 64,
            config=primary_config(),
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(Gate11ProtocolError):
                run_campaign(
                    context,
                    CampaignPaths(Path(directory) / "primary"),
                    worker_count=1,
                    invocation_id="unauthorized-primary",
                )
            self.assertFalse((Path(directory) / "primary").exists())


if __name__ == "__main__":
    unittest.main()
