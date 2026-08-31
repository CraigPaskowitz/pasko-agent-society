"""Atomic, resumable, hash-verifiable Gate 2 evidence storage."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from ..canonical import canonical_hash
from .evidence import verify_content_hash
from .protocol import (
    ANALYZED_PAIR_COUNT,
    PAIR_POOL_COUNT,
    Gate2Config,
    Gate2InvariantError,
    Gate2ProtocolError,
    production_config,
    run_condition_from_behaviors,
    validate_condition_result,
    validate_pair_id,
    validate_request_record,
)


CHECKPOINT_SCHEMA = "gate2-checkpoint-v1"
POPULATION_CHUNK_SCHEMA = "gate2-population-chunk-v1"
COMPLETION_MANIFEST_SCHEMA = "gate2-completion-manifest-v1"


class EvidenceIntegrityError(RuntimeError):
    """A Gate 2 evidence object cannot be trusted."""


class CampaignIncompleteError(RuntimeError):
    """The frozen campaign is incomplete or invalid for inference."""


FailureHook = Callable[[str], None]


@dataclass(frozen=True)
class CampaignContext:
    campaign_id: str
    campaign_spec_hash: str
    implementation_commit: str
    implementation_source_hash: str
    config: Gate2Config


def fixture_context(config: Gate2Config) -> CampaignContext:
    if config.campaign_namespace != "fixture":
        raise Gate2ProtocolError("Fixture context requires the fixture namespace")
    return CampaignContext(
        campaign_id=config.campaign_id,
        campaign_spec_hash=canonical_hash({"fixture_config": config}),
        implementation_commit="fixture-implementation",
        implementation_source_hash=canonical_hash("fixture-source"),
        config=config,
    )


@dataclass(frozen=True)
class CampaignPaths:
    root: Path

    @property
    def requests(self) -> Path:
        return self.root / "requests"

    @property
    def attempts(self) -> Path:
        return self.root / "attempts"

    @property
    def populations(self) -> Path:
        return self.root / "populations"

    @property
    def locks(self) -> Path:
        return self.root / "locks"

    @property
    def checkpoint(self) -> Path:
        return self.root / "checkpoint.json"

    @property
    def completion_manifest(self) -> Path:
        return self.root / "completion-manifest.json"

    @property
    def primary_analysis(self) -> Path:
        return self.root / "primary-analysis.json"


def safe_slot_name(logical_slot_id: str) -> str:
    if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:" for character in logical_slot_id):
        raise Gate2ProtocolError("Logical slot ID contains an unsafe character")
    return logical_slot_id.replace(":", "__")


def request_path(paths: CampaignPaths, logical_slot_id: str) -> Path:
    return paths.requests / f"{safe_slot_name(logical_slot_id)}.json"


def attempt_directory(paths: CampaignPaths, logical_slot_id: str) -> Path:
    return paths.attempts / safe_slot_name(logical_slot_id)


def attempt_reservation_path(paths: CampaignPaths, logical_slot_id: str, attempt: int) -> Path:
    return attempt_directory(paths, logical_slot_id) / f"attempt-{attempt}-reservation.json"


def attempt_result_path(paths: CampaignPaths, logical_slot_id: str, attempt: int) -> Path:
    return attempt_directory(paths, logical_slot_id) / f"attempt-{attempt}-result.json"


def population_path(paths: CampaignPaths, pair_id: str) -> Path:
    return paths.populations / f"{pair_id}.json"


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceIntegrityError(f"Unreadable JSON evidence: {path.name}") from error
    if not isinstance(value, Mapping):
        raise EvidenceIntegrityError(f"JSON evidence is not an object: {path.name}")
    return value


def atomic_write_json(
    path: Path,
    value: Mapping[str, Any],
    *,
    validator: Callable[[Mapping[str, Any]], None] | None = None,
    failure_hook: FailureHook | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        if failure_hook:
            failure_hook("before-atomic-publication")
        if validator:
            validator(read_json(temporary))
        os.replace(temporary, path)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def publish_immutable(path: Path, value: Mapping[str, Any], *, validator: Callable[[Mapping[str, Any]], None]) -> str:
    if path.exists():
        existing = read_json(path)
        validator(existing)
        if existing != value:
            raise EvidenceIntegrityError(f"Immutable evidence collision: {path.name}")
        return "resumed"
    atomic_write_json(path, value, validator=validator)
    return "newly_published"


def publish_request(
    repository_root: Path,
    context: CampaignContext,
    paths: CampaignPaths,
    record: Mapping[str, Any],
) -> str:
    logical_slot_id = str(record["logical_slot_id"])

    def validator(value: Mapping[str, Any]) -> None:
        validate_request_record(repository_root, context.config, value)
        if value["logical_slot_id"] != logical_slot_id:
            raise EvidenceIntegrityError("Request identity differs from its path")

    return publish_immutable(request_path(paths, logical_slot_id), record, validator=validator)


def publish_attempt_reservation(paths: CampaignPaths, reservation: Mapping[str, Any]) -> str:
    verify_content_hash(reservation)
    logical_slot_id = str(reservation["logical_slot_id"])
    attempt = int(reservation["attempt_number"])
    if not 1 <= attempt <= 3:
        raise EvidenceIntegrityError("Attempt number lies outside the frozen retry policy")
    return publish_immutable(
        attempt_reservation_path(paths, logical_slot_id, attempt),
        reservation,
        validator=verify_content_hash,
    )


def publish_attempt_result(paths: CampaignPaths, result: Mapping[str, Any]) -> str:
    verify_content_hash(result)
    logical_slot_id = str(result["logical_slot_id"])
    attempt = int(result["attempt_number"])
    reservation_path = attempt_reservation_path(paths, logical_slot_id, attempt)
    if not reservation_path.exists():
        raise EvidenceIntegrityError("Attempt result has no prior dispatch reservation")
    reservation = read_json(reservation_path)
    verify_content_hash(reservation)
    for key in ("logical_slot_id", "request_record_hash", "request_content_hash", "attempt_number"):
        if result.get(key) != reservation.get(key):
            raise EvidenceIntegrityError("Attempt result differs from its reservation")
    return publish_immutable(
        attempt_result_path(paths, logical_slot_id, attempt),
        result,
        validator=verify_content_hash,
    )


def attempt_results(paths: CampaignPaths, logical_slot_id: str) -> list[Mapping[str, Any]]:
    directory = attempt_directory(paths, logical_slot_id)
    if not directory.exists():
        return []
    results = []
    for path in sorted(directory.glob("attempt-*-result.json")):
        value = read_json(path)
        verify_content_hash(value)
        results.append(value)
    numbers = [int(item["attempt_number"]) for item in results]
    if numbers != sorted(set(numbers)) or any(not 1 <= number <= 3 for number in numbers):
        raise EvidenceIntegrityError("Attempt result sequence is duplicate or malformed")
    return results


def terminal_behavior(paths: CampaignPaths, logical_slot_id: str) -> Mapping[str, Any] | None:
    results = attempt_results(paths, logical_slot_id)
    valid = [item for item in results if bool(item.get("behavioral_valid"))]
    if len(valid) > 1:
        raise EvidenceIntegrityError("Logical slot has multiple behavioral responses")
    if valid:
        winner = valid[0]
        if any(int(item["attempt_number"]) > int(winner["attempt_number"]) for item in results):
            raise EvidenceIntegrityError("An attempt occurred after valid behavior")
        return {
            "disposition": winner["disposition"],
            "action_type": winner["action_type"],
            "evidence_hash": winner["content_hash"],
            "attempt_number": winner["attempt_number"],
        }
    return None


def build_population_chunk(
    context: CampaignContext,
    pair_id: str,
    slot_records: Sequence[Mapping[str, Any]],
    *,
    condition_results: Mapping[str, Mapping[str, Any]] | None,
    invalid_reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    validate_pair_id(context.config, pair_id)
    valid = condition_results is not None and not invalid_reason_codes
    base = {
        "schema_version": POPULATION_CHUNK_SCHEMA,
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "pair_id": pair_id,
        "technical_validity": "VALID" if valid else "TECHNICALLY_INVALID",
        "slot_records": sorted((dict(item) for item in slot_records), key=lambda item: str(item["logical_slot_id"])),
        "condition_results": dict(condition_results) if condition_results is not None else None,
        "invalid_reason_codes": sorted(set(invalid_reason_codes)),
    }
    base["content_hash"] = canonical_hash(base)
    validate_population_chunk(context, base)
    return base


def validate_population_chunk(context: CampaignContext, chunk: Mapping[str, Any]) -> None:
    identity = dict(chunk)
    supplied = identity.pop("content_hash", None)
    if supplied != canonical_hash(identity):
        raise EvidenceIntegrityError("Population chunk content hash differs")
    required = {
        "schema_version", "campaign_id", "campaign_spec_hash", "implementation_commit",
        "implementation_source_hash", "pair_id", "technical_validity", "slot_records",
        "condition_results", "invalid_reason_codes", "content_hash",
    }
    if set(chunk) != required or chunk.get("schema_version") != POPULATION_CHUNK_SCHEMA:
        raise EvidenceIntegrityError("Population chunk schema differs")
    for key, expected in {
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
    }.items():
        if chunk.get(key) != expected:
            raise EvidenceIntegrityError("Population chunk authority differs")
    pair_id = str(chunk["pair_id"])
    validate_pair_id(context.config, pair_id)
    records = chunk["slot_records"]
    if not isinstance(records, list):
        raise EvidenceIntegrityError("Population slot records are malformed")
    slot_ids = [item.get("logical_slot_id") for item in records if isinstance(item, Mapping)]
    if len(slot_ids) != len(records) or len(slot_ids) != len(set(slot_ids)):
        raise EvidenceIntegrityError("Population slot identities are duplicate or malformed")
    if chunk["technical_validity"] == "VALID":
        if len(records) != context.config.logical_slots_per_pair or chunk["invalid_reason_codes"]:
            raise EvidenceIntegrityError("Valid population does not contain every logical slot")
        by_condition: dict[str, dict[str, Mapping[str, Any]]] = {"T2": {}, "T5": {}}
        for item in records:
            if item.get("pair_id") != pair_id or item.get("condition") not in by_condition:
                raise EvidenceIntegrityError("Population slot identity differs")
            behavior = item.get("behavior")
            if not isinstance(behavior, Mapping) or behavior.get("disposition") not in {"VALID_ACTION", "EXPLICIT_REFUSAL"}:
                raise EvidenceIntegrityError("Valid population contains technical output")
            by_condition[str(item["condition"])][str(item["target_agent_id"])] = behavior
        if any(set(values) != set(context.config.target_ids) for values in by_condition.values()):
            raise EvidenceIntegrityError("Valid population target matching differs")
        conditions = chunk["condition_results"]
        if not isinstance(conditions, Mapping) or set(conditions) != {"T2", "T5"}:
            raise EvidenceIntegrityError("Valid population condition results differ")
        for condition in ("T2", "T5"):
            validate_condition_result(context.config, conditions[condition])
            replay = run_condition_from_behaviors(context.config, pair_id, condition, by_condition[condition])
            if replay != conditions[condition]:
                raise EvidenceIntegrityError("Environment replay differs from frozen response corpus")
    elif chunk["technical_validity"] == "TECHNICALLY_INVALID":
        if chunk["condition_results"] is not None or not chunk["invalid_reason_codes"]:
            raise EvidenceIntegrityError("Invalid population evidence is incomplete")
    else:
        raise EvidenceIntegrityError("Unknown population technical validity")


def publish_population_chunk(
    context: CampaignContext,
    paths: CampaignPaths,
    chunk: Mapping[str, Any],
    *,
    failure_hook: FailureHook | None = None,
) -> str:
    pair_id = str(chunk["pair_id"])
    lock_path = paths.locks / f"{pair_id}.lock"
    with file_lock(lock_path):
        path = population_path(paths, pair_id)
        if path.exists():
            existing = read_json(path)
            validate_population_chunk(context, existing)
            if existing != chunk:
                raise EvidenceIntegrityError("Population chunk collision")
            return "resumed"
        if failure_hook:
            failure_hook("before-population-publication")
        atomic_write_json(path, chunk, validator=lambda value: validate_population_chunk(context, value), failure_hook=failure_hook)
        return "newly_published"


@dataclass(frozen=True)
class CampaignScan:
    valid_pair_ids: tuple[str, ...]
    invalid_pair_ids: tuple[str, ...]
    missing_pair_ids: tuple[str, ...]
    invalid_files: tuple[str, ...]
    ordered_chunk_hashes: tuple[str, ...]


def scan_campaign(context: CampaignContext, paths: CampaignPaths) -> CampaignScan:
    valid: list[str] = []
    invalid: list[str] = []
    invalid_files: list[str] = []
    hashes: list[str] = []
    seen: set[str] = set()
    if paths.populations.exists():
        for path in sorted(paths.populations.glob("*.json")):
            try:
                chunk = read_json(path)
                validate_population_chunk(context, chunk)
                pair_id = str(chunk["pair_id"])
                if path.name != f"{pair_id}.json" or pair_id in seen:
                    raise EvidenceIntegrityError("Population path or identity is duplicate")
                seen.add(pair_id)
                hashes.append(str(chunk["content_hash"]))
                (valid if chunk["technical_validity"] == "VALID" else invalid).append(pair_id)
            except (EvidenceIntegrityError, Gate2InvariantError, Gate2ProtocolError):
                invalid_files.append(path.name)
    expected = [context.config.pair_id(index) for index in range(context.config.pair_pool_count)]
    missing = [pair_id for pair_id in expected if pair_id not in seen]
    return CampaignScan(tuple(valid), tuple(invalid), tuple(missing), tuple(invalid_files), tuple(hashes))


def _checkpoint_mapping(context: CampaignContext, scan: CampaignScan) -> dict[str, Any]:
    value = {
        "schema_version": CHECKPOINT_SCHEMA,
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "valid_completed": len(scan.valid_pair_ids),
        "technical_invalid": len(scan.invalid_pair_ids),
        "pending_pool": len(scan.missing_pair_ids),
        "valid_pair_ids": list(scan.valid_pair_ids),
        "technical_invalid_pair_ids": list(scan.invalid_pair_ids),
        "ordered_chunk_hashes": list(scan.ordered_chunk_hashes),
        "integrity_status": "PASS" if not scan.invalid_files else "FAIL",
    }
    value["content_hash"] = canonical_hash(value)
    return value


def rebuild_checkpoint(context: CampaignContext, paths: CampaignPaths, *, failure_hook: FailureHook | None = None) -> dict[str, Any]:
    scan = scan_campaign(context, paths)
    if scan.invalid_files:
        raise EvidenceIntegrityError("Invalid population files block checkpoint reconstruction")
    checkpoint = _checkpoint_mapping(context, scan)
    if failure_hook:
        failure_hook("during-checkpoint-reconstruction")
    atomic_write_json(paths.checkpoint, checkpoint, validator=verify_content_hash)
    return checkpoint


def _included_pair_ids(context: CampaignContext, scan: CampaignScan) -> tuple[str, ...]:
    status = {pair_id: "VALID" for pair_id in scan.valid_pair_ids} | {
        pair_id: "INVALID" for pair_id in scan.invalid_pair_ids
    }
    included = []
    for index in range(context.config.pair_pool_count):
        pair_id = context.config.pair_id(index)
        if pair_id not in status:
            break
        if status[pair_id] == "VALID":
            included.append(pair_id)
            if len(included) == context.config.analyzed_pair_count:
                return tuple(included)
    return tuple(included)


def publish_completion_manifest(context: CampaignContext, paths: CampaignPaths) -> dict[str, Any]:
    scan = scan_campaign(context, paths)
    if scan.invalid_files:
        raise CampaignIncompleteError("Invalid population files block campaign completion")
    included = _included_pair_ids(context, scan)
    if len(included) != context.config.analyzed_pair_count:
        raise CampaignIncompleteError("Fewer than 200 technically valid populations are complete")
    last_index = validate_pair_id(context.config, included[-1])
    processed = [context.config.pair_id(index) for index in range(last_index + 1)]
    present = set(scan.valid_pair_ids) | set(scan.invalid_pair_ids)
    if any(pair_id not in present for pair_id in processed):
        raise CampaignIncompleteError("Population eligibility order has a gap")
    chunks = []
    request_hashes: list[str] = []
    attempt_hashes: list[str] = []
    seen_logical_slots: set[str] = set()
    seen_provider_response_ids: set[str] = set()
    total_attempts = 0
    input_tokens = cached_input_tokens = output_tokens = 0
    for pair_id in processed:
        chunk = read_json(population_path(paths, pair_id))
        validate_population_chunk(context, chunk)
        chunks.append({"pair_id": pair_id, "technical_validity": chunk["technical_validity"], "content_hash": chunk["content_hash"]})
        for slot in chunk["slot_records"]:
            logical_slot = str(slot["logical_slot_id"])
            if logical_slot in seen_logical_slots:
                raise EvidenceIntegrityError("Duplicate logical slot enters completion evidence")
            seen_logical_slots.add(logical_slot)
            req = read_json(request_path(paths, logical_slot))
            verify_content_hash(req)
            if req.get("content_hash") != slot.get("request_record_hash"):
                raise EvidenceIntegrityError("Population request reference differs")
            request_hashes.append(str(req["content_hash"]))
            attempts = attempt_results(paths, logical_slot)
            if [item["content_hash"] for item in attempts] != slot.get("attempt_hashes"):
                raise EvidenceIntegrityError("Population attempt references differ")
            for attempt in attempts:
                attempt_hashes.append(str(attempt["content_hash"]))
                total_attempts += 1
                response_id = attempt.get("provider_response_id")
                if response_id is not None:
                    if response_id in seen_provider_response_ids:
                        raise EvidenceIntegrityError("Provider response ID is duplicated")
                    seen_provider_response_ids.add(str(response_id))
                usage = attempt.get("usage") if isinstance(attempt.get("usage"), Mapping) else {}
                input_tokens += int(usage.get("input_tokens", 0) or 0)
                output_tokens += int(usage.get("output_tokens", 0) or 0)
                details = usage.get("input_tokens_details")
                if isinstance(details, Mapping):
                    cached_input_tokens += int(details.get("cached_tokens", 0) or 0)
    if not 0 <= cached_input_tokens <= input_tokens:
        raise EvidenceIntegrityError("Cached-input accounting is impossible")
    value = {
        "schema_version": COMPLETION_MANIFEST_SCHEMA,
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "included_pair_ids": list(included),
        "excluded_technical_pair_ids": [pair_id for pair_id in processed if pair_id in scan.invalid_pair_ids],
        "processed_pair_ids": processed,
        "valid_pair_count": len(included),
        "condition_run_count": len(included) * 2,
        "valid_behavioral_slot_count": len(included) * context.config.logical_slots_per_pair,
        "processed_logical_slot_count": len(seen_logical_slots),
        "provider_attempt_count": total_attempts,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "output_tokens": output_tokens,
        "ordered_population_chunks": chunks,
        "ordered_population_ensemble_hash": canonical_hash(chunks),
        "ordered_request_evidence_hash": canonical_hash(request_hashes),
        "ordered_attempt_evidence_hash": canonical_hash(attempt_hashes),
        "integrity_status": "PASS",
    }
    value["content_hash"] = canonical_hash(value)
    atomic_write_json(paths.completion_manifest, value, validator=verify_content_hash)
    return value


def verify_completion_manifest(context: CampaignContext, paths: CampaignPaths) -> Mapping[str, Any]:
    if not paths.completion_manifest.exists():
        raise CampaignIncompleteError("Completion manifest is absent")
    existing = read_json(paths.completion_manifest)
    verify_content_hash(existing)
    expected = publish_completion_manifest(context, paths)
    if existing != expected:
        raise EvidenceIntegrityError("Completion manifest differs from reconstruction")
    return existing


def operational_status(context: CampaignContext, paths: CampaignPaths) -> dict[str, Any]:
    scan = scan_campaign(context, paths)
    included = _included_pair_ids(context, scan)
    return {
        "campaign_id": context.campaign_id,
        "valid_completed": len(included),
        "technical_invalid": len(scan.invalid_pair_ids),
        "pending_required": max(0, context.config.analyzed_pair_count - len(included)),
        "remaining_frozen_pool": len(scan.missing_pair_ids),
        "checkpoint_hash": read_json(paths.checkpoint).get("content_hash") if paths.checkpoint.exists() else None,
        "integrity_status": "PASS" if not scan.invalid_files else "FAIL",
    }
