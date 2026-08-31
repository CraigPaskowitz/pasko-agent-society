from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pasko_agent_society.gate2.protocol import MODEL_ID, fixture_config
from pasko_agent_society.gate2.evidence import build_attempt_reservation
from pasko_agent_society.gate2.protocol import build_request_record
from pasko_agent_society.gate2.runner import Gate2BudgetBlocker, TransportOutcome, conservative_attempt_cost, run_campaign
from pasko_agent_society.gate2.storage import (
    CampaignIncompleteError,
    CampaignPaths,
    EvidenceIntegrityError,
    fixture_context,
    atomic_write_json,
    operational_status,
    publish_attempt_reservation,
    publish_request,
    publish_completion_manifest,
    read_json,
    verify_completion_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class FixtureTransport:
    def __init__(self, scripted_failures=(), *, refusal=False):
        self.scripted_failures = list(scripted_failures)
        self.refusal = refusal
        self.calls = 0

    def __call__(self, _body, _timeout):
        self.calls += 1
        if self.scripted_failures:
            kind = self.scripted_failures.pop(0)
            if kind == "http500":
                return TransportOutcome(500, {"error": {"type": "server_error"}}, "HTTP_500", "fixture", True)
            if kind == "malformed":
                return TransportOutcome(200, self._response(output_text="not json"))
        if self.refusal:
            return TransportOutcome(200, self._response(refusal="fixture refusal"))
        return TransportOutcome(200, self._response(output_text='{"action_type":"ABSTAIN"}'))

    def _response(self, *, output_text=None, refusal=None):
        content = []
        if output_text is not None:
            content.append({"type": "output_text", "text": output_text})
        if refusal is not None:
            content.append({"type": "refusal", "refusal": refusal})
        return {
            "id": f"resp-fixture-{self.calls:05d}",
            "model": MODEL_ID,
            "service_tier": "default",
            "status": "completed",
            "usage": {"input_tokens": 10, "output_tokens": 2, "input_tokens_details": {"cached_tokens": 0}},
            "output": [{"type": "message", "status": "completed", "content": content}],
        }


class Gate2StorageRunnerTests(unittest.TestCase):
    @staticmethod
    def config(**changes):
        defaults = {
            "analyzed_pair_count": 1,
            "reserve_pair_count": 0,
            "population_size": 4,
            "source_count": 2,
            "target_count": 2,
            "worker_count": 1,
        }
        defaults.update(changes)
        return fixture_config(**defaults)

    def test_refusal_is_valid_and_never_retried(self) -> None:
        context = fixture_context(self.config())
        transport = FixtureTransport(refusal=True)
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            result = run_campaign(
                ROOT, context, paths, transport=transport, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None
            )
            self.assertEqual(result["valid_completed"], 1)
            self.assertEqual(transport.calls, 4)
            chunk = read_json(paths.populations / "fixture-pair-000.json")
            self.assertEqual({item["behavior"]["disposition"] for item in chunk["slot_records"]}, {"EXPLICIT_REFUSAL"})
            self.assertEqual(chunk["condition_results"]["T2"]["boundary_attempt_count"], 0)

    def test_technical_and_malformed_failures_retry_then_accept_behavior(self) -> None:
        for failure in ("http500", "malformed"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                context = fixture_context(self.config())
                transport = FixtureTransport([failure])
                paths = CampaignPaths(Path(directory))
                run_campaign(
                    ROOT, context, paths, transport=transport, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None
                )
                self.assertEqual(transport.calls, 5)
                self.assertEqual(operational_status(context, paths)["valid_completed"], 1)

    def test_unresolved_technical_population_uses_only_frozen_reserve_order(self) -> None:
        context = fixture_context(self.config(reserve_pair_count=1))
        transport = FixtureTransport(["http500", "http500", "http500"])
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            result = run_campaign(
                ROOT, context, paths, transport=transport, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None
            )
            self.assertEqual(result["valid_completed"], 1)
            self.assertEqual(result["technical_invalid"], 1)
            completion = publish_completion_manifest(context, paths)
            self.assertEqual(completion["included_pair_ids"], ["fixture-pair-001"])
            self.assertEqual(completion["excluded_technical_pair_ids"], ["fixture-pair-000"])
            self.assertEqual(completion["cached_input_tokens"], 0)
            self.assertEqual(verify_completion_manifest(context, paths), completion)

    def test_no_partial_population_enters_inference(self) -> None:
        context = fixture_context(self.config(reserve_pair_count=0))
        transport = FixtureTransport(["http500", "http500", "http500"])
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            result = run_campaign(
                ROOT, context, paths, transport=transport, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None
            )
            self.assertEqual(result["campaign_disposition"], "INVALID_INCONCLUSIVE")
            with self.assertRaises(CampaignIncompleteError):
                publish_completion_manifest(context, paths)

    def test_restart_resumes_complete_population_without_provider_calls(self) -> None:
        context = fixture_context(self.config())
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            first = FixtureTransport()
            run_campaign(ROOT, context, paths, transport=first, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None)
            second = FixtureTransport()
            run_campaign(ROOT, context, paths, transport=second, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None)
            self.assertEqual(first.calls, 4)
            self.assertEqual(second.calls, 0)

    def test_interrupted_reserved_attempt_is_retained_and_retry_uses_same_slot(self) -> None:
        context = fixture_context(self.config())
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            pair_id = context.config.pair_id(0)
            target = context.config.target_ids[0]
            condition = "T2"
            request = build_request_record(ROOT, context.config, pair_id, target, condition)
            publish_request(ROOT, context, paths, request)
            reservation = build_attempt_reservation(
                logical_slot_id=request["logical_slot_id"],
                request_record_hash=request["content_hash"],
                request_content_hash=request["request_content_hash"],
                attempt_number=1,
                reserved_at="2026-08-30T00:00:00Z",
                conservative_cost_debit_usd=conservative_attempt_cost(),
            )
            publish_attempt_reservation(paths, reservation)
            transport = FixtureTransport()
            run_campaign(ROOT, context, paths, transport=transport, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None)
            recovered = read_json(paths.attempts / request["logical_slot_id"].replace(":", "__") / "attempt-1-result.json")
            self.assertEqual(recovered["technical_error_code"], "INTERRUPTED_AFTER_DISPATCH_RESERVATION")
            self.assertEqual(transport.calls, 4)

    def test_budget_ceiling_blocks_before_provider_dispatch(self) -> None:
        context = fixture_context(self.config(hard_cost_ceiling_usd=conservative_attempt_cost() / 2))
        transport = FixtureTransport()
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            with self.assertRaises(Gate2BudgetBlocker):
                run_campaign(ROOT, context, paths, transport=transport, input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None)
            self.assertEqual(transport.calls, 0)

    def test_atomic_failure_never_publishes_partial_final(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"

            def fail(stage):
                if stage == "before-atomic-publication":
                    raise RuntimeError("fixture interruption")

            with self.assertRaises(RuntimeError):
                atomic_write_json(path, {"value": 1}, failure_hook=fail)
            self.assertFalse(path.exists())
            self.assertEqual(len(list(path.parent.glob(".evidence.*.tmp"))), 1)

    def test_corrupt_population_blocks_integrity(self) -> None:
        context = fixture_context(self.config())
        with tempfile.TemporaryDirectory() as directory:
            paths = CampaignPaths(Path(directory))
            run_campaign(ROOT, context, paths, transport=FixtureTransport(), input_token_counts={"T2": 1, "T5": 1}, sleep=lambda _: None)
            path = paths.populations / "fixture-pair-000.json"
            value = json.loads(path.read_text())
            value["content_hash"] = "sha256:" + "0" * 64
            path.write_text(json.dumps(value))
            with self.assertRaises(CampaignIncompleteError):
                publish_completion_manifest(context, paths)


if __name__ == "__main__":
    unittest.main()
