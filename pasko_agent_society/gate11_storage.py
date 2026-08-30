"""Atomic, resumable, hash-verifiable Gate 1.1 campaign storage."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from .canonical import canonical_hash, canonical_json
from .gate11_manifest import AUTHORIZATION_SCHEMA, CampaignSpec
from .gate11_protocol import (
    PAIR_CHUNK_SCHEMA,
    Gate11Config,
    Gate11InvariantError,
    Gate11ProtocolError,
    run_pair,
    validate_pair_id,
    validate_pair_result,
)


CHECKPOINT_SCHEMA = "gate11-checkpoint-v1"
COMPLETION_MANIFEST_SCHEMA = "gate11-completion-manifest-v1"
INVOCATION_JOURNAL_SCHEMA = "gate11-invocation-journal-v1"

FailureHook = Callable[[str], None]
PairComputer = Callable[[Gate11Config, str], Mapping[str, Any]]


class ChunkIntegrityError(RuntimeError):
    """A final chunk, checkpoint, or completion record cannot be trusted."""


class CampaignIncompleteError(RuntimeError):
    """The campaign is not complete and valid enough for analysis."""


@dataclass(frozen=True)
class CampaignContext:
    campaign_id: str
    campaign_spec_hash: str
    implementation_commit: str
    implementation_source_hash: str
    config: Gate11Config

    @classmethod
    def from_spec(cls, spec: CampaignSpec) -> "CampaignContext":
        if not spec.is_certified_candidate:
            raise Gate11ProtocolError("Campaign implementation is not a certified candidate")
        return cls(
            campaign_id=spec.campaign_id,
            campaign_spec_hash=spec.spec_hash,
            implementation_commit=spec.implementation_commit,
            implementation_source_hash=spec.implementation_source_hash,
            config=spec.config,
        )


def fixture_context(config: Gate11Config) -> CampaignContext:
    if config.campaign_namespace != "fixture":
        raise Gate11ProtocolError("Fixture context requires the fixture RNG namespace")
    return CampaignContext(
        campaign_id="gate11-fixture-campaign",
        campaign_spec_hash=canonical_hash({"fixture_config": config}),
        implementation_commit="fixture-implementation",
        implementation_source_hash=canonical_hash("fixture-source"),
        config=config,
    )


@dataclass(frozen=True)
class CampaignPaths:
    root: Path

    @property
    def chunks(self) -> Path:
        return self.root / "chunks"

    @property
    def locks(self) -> Path:
        return self.root / "locks"

    @property
    def journals(self) -> Path:
        return self.root / "journals"

    @property
    def checkpoint(self) -> Path:
        return self.root / "checkpoint.json"

    @property
    def checkpoint_lock(self) -> Path:
        return self.locks / "checkpoint.lock"

    @property
    def completion_manifest(self) -> Path:
        return self.root / "completion-manifest.json"

    @property
    def primary_analysis(self) -> Path:
        return self.root / "primary-analysis.json"


def paths_from_spec(repository_root: Path, spec: CampaignSpec) -> CampaignPaths:
    relative = spec.artifact_root
    if relative.is_absolute() or ".." in relative.parts:
        raise Gate11ProtocolError("Campaign artifact root is not repository-relative")
    return CampaignPaths(repository_root / Path(*relative.parts))


def _content_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "content_hash"}


def add_content_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(value)
    if "content_hash" in output:
        raise Gate11ProtocolError("Content hash must not be supplied by the caller")
    output["content_hash"] = canonical_hash(output)
    return output


def verify_content_hash(value: Mapping[str, Any]) -> None:
    if value.get("content_hash") != canonical_hash(_content_identity(value)):
        raise ChunkIntegrityError("Canonical content hash differs")


def build_pair_chunk(
    context: CampaignContext,
    pair_id: str,
    pair_result: Mapping[str, Any] | None,
    *,
    invalid_reason: str | None = None,
) -> dict[str, Any]:
    validate_pair_id(context.config, pair_id)
    if (pair_result is None) == (invalid_reason is None):
        raise Gate11ProtocolError("A chunk must be either valid or explicitly invalid")
    base = {
        "schema_version": PAIR_CHUNK_SCHEMA,
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "pair_id": pair_id,
        "validity_status": "VALID" if pair_result is not None else "SIMULATOR_INVARIANT_FAILURE",
        "pair_result": pair_result,
        "invalid_reason": invalid_reason,
    }
    chunk = add_content_hash(base)
    validate_pair_chunk(context, chunk, expected_pair_id=pair_id)
    return chunk


def compute_pair_chunk(
    context: CampaignContext,
    pair_id: str,
    *,
    computer: PairComputer = run_pair,
) -> dict[str, Any]:
    try:
        result = computer(context.config, pair_id)
    except Gate11InvariantError as error:
        return build_pair_chunk(
            context,
            pair_id,
            None,
            invalid_reason=str(error),
        )
    return build_pair_chunk(context, pair_id, result)


def validate_pair_chunk(
    context: CampaignContext,
    chunk: Mapping[str, Any],
    *,
    expected_pair_id: str | None = None,
) -> None:
    required = {
        "schema_version",
        "campaign_id",
        "campaign_spec_hash",
        "implementation_commit",
        "implementation_source_hash",
        "pair_id",
        "validity_status",
        "pair_result",
        "invalid_reason",
        "content_hash",
    }
    if set(chunk) != required or chunk.get("schema_version") != PAIR_CHUNK_SCHEMA:
        raise ChunkIntegrityError("Pair chunk schema has missing or unknown fields")
    verify_content_hash(chunk)
    pair_id = str(chunk["pair_id"])
    validate_pair_id(context.config, pair_id)
    if expected_pair_id is not None and pair_id != expected_pair_id:
        raise ChunkIntegrityError("Pair chunk identity differs from its filename")
    identities = {
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
    }
    if any(chunk[key] != expected for key, expected in identities.items()):
        raise ChunkIntegrityError("Pair chunk campaign or implementation identity differs")
    status = chunk["validity_status"]
    if status == "VALID":
        if chunk["pair_result"] is None or chunk["invalid_reason"] is not None:
            raise ChunkIntegrityError("Valid chunk payload is incomplete")
        validate_pair_result(context.config, chunk["pair_result"])
        if chunk["pair_result"]["pair_id"] != pair_id:
            raise ChunkIntegrityError("Pair result identity differs from its chunk")
    elif status == "SIMULATOR_INVARIANT_FAILURE":
        if chunk["pair_result"] is not None or not isinstance(chunk["invalid_reason"], str):
            raise ChunkIntegrityError("Invalid completed chunk diagnostic is malformed")
    else:
        raise ChunkIntegrityError("Unknown chunk validity status")


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ChunkIntegrityError(f"Unreadable JSON artifact: {path.name}") from error
    if not isinstance(value, Mapping):
        raise ChunkIntegrityError(f"JSON artifact is not an object: {path.name}")
    return value


def atomic_write_json(
    path: Path,
    value: Mapping[str, Any],
    *,
    validator: Callable[[Mapping[str, Any]], None] | None = None,
    failure_hook: FailureHook | None = None,
) -> None:
    """Publish one complete JSON object or leave the previous final file untouched."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        if failure_hook is not None:
            failure_hook("before-atomic-publication")
        decoded = _read_json(temporary)
        if validator is not None:
            validator(decoded)
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        # An interrupted temporary file is deliberately preserved for audit.
        raise


@contextmanager
def advisory_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def pair_chunk_path(paths: CampaignPaths, pair_id: str) -> Path:
    return paths.chunks / f"{pair_id}.json"


def load_pair_chunk(
    context: CampaignContext,
    path: Path,
    *,
    expected_pair_id: str | None = None,
) -> Mapping[str, Any]:
    chunk = _read_json(path)
    validate_pair_chunk(context, chunk, expected_pair_id=expected_pair_id)
    return chunk


@dataclass(frozen=True)
class CampaignScan:
    valid_chunk_hashes: Mapping[str, str]
    invalid_pair_ids: tuple[str, ...]
    invalid_files: tuple[str, ...]
    duplicate_pair_ids: tuple[str, ...]
    missing_pair_ids: tuple[str, ...]
    temporary_files: tuple[str, ...]

    @property
    def completed_count(self) -> int:
        return len(self.valid_chunk_hashes) + len(self.invalid_pair_ids)

    @property
    def pending_count(self) -> int:
        return len(self.missing_pair_ids)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_pair_ids) + len(self.invalid_files)

    @property
    def integrity_ok(self) -> bool:
        return not self.invalid_files and not self.duplicate_pair_ids


def scan_campaign(context: CampaignContext, paths: CampaignPaths) -> CampaignScan:
    expected = {context.config.pair_id(index) for index in range(context.config.pair_count)}
    valid: dict[str, str] = {}
    invalid_pairs: set[str] = set()
    invalid_files: list[str] = []
    seen: Counter[str] = Counter()
    if paths.chunks.exists():
        for path in sorted(paths.chunks.glob("*.json"), key=lambda item: item.name):
            try:
                chunk = _read_json(path)
                pair_id = str(chunk.get("pair_id", ""))
                if pair_id:
                    seen[pair_id] += 1
                if pair_id not in expected or path.name != f"{pair_id}.json":
                    raise ChunkIntegrityError("Chunk filename or pair identity differs")
                validate_pair_chunk(context, chunk, expected_pair_id=pair_id)
                if chunk["validity_status"] == "VALID":
                    valid[pair_id] = str(chunk["content_hash"])
                else:
                    invalid_pairs.add(pair_id)
            except (ChunkIntegrityError, Gate11InvariantError, Gate11ProtocolError):
                invalid_files.append(path.name)
    duplicates = tuple(sorted(pair_id for pair_id, count in seen.items() if count > 1))
    completed = set(valid) | invalid_pairs
    temporary = (
        tuple(sorted(path.name for path in paths.chunks.glob(".*.tmp")))
        if paths.chunks.exists()
        else ()
    )
    return CampaignScan(
        valid_chunk_hashes=dict(sorted(valid.items())),
        invalid_pair_ids=tuple(sorted(invalid_pairs)),
        invalid_files=tuple(sorted(invalid_files)),
        duplicate_pair_ids=duplicates,
        missing_pair_ids=tuple(sorted(expected - completed)),
        temporary_files=temporary,
    )


def operational_status(context: CampaignContext, paths: CampaignPaths) -> dict[str, Any]:
    scan = scan_campaign(context, paths)
    checkpoint_hash: str | None = None
    checkpoint_ok = True
    if paths.checkpoint.exists():
        try:
            checkpoint = _read_json(paths.checkpoint)
            validate_checkpoint(context, checkpoint)
            checkpoint_hash = str(checkpoint["content_hash"])
        except ChunkIntegrityError:
            checkpoint_ok = False
    return {
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "completed": scan.completed_count,
        "pending": scan.pending_count,
        "invalid": scan.invalid_count,
        "resumed": 0,
        "newly_executed": 0,
        "interrupted": len(scan.temporary_files),
        "recomputed": 0,
        "integrity_status": "PASS" if scan.integrity_ok and checkpoint_ok else "FAIL",
        "checkpoint_hash": checkpoint_hash,
    }


def checkpoint_value(context: CampaignContext, scan: CampaignScan) -> dict[str, Any]:
    base = {
        "schema_version": CHECKPOINT_SCHEMA,
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "counts": {
            "completed": scan.completed_count,
            "pending": scan.pending_count,
            "invalid": scan.invalid_count,
            "interrupted_temporary_files": len(scan.temporary_files),
        },
        "ordered_valid_chunk_hashes_hash": canonical_hash(
            [scan.valid_chunk_hashes[pair_id] for pair_id in sorted(scan.valid_chunk_hashes)]
        ),
        "valid_chunk_hashes": dict(sorted(scan.valid_chunk_hashes.items())),
        "valid_pair_ids": list(sorted(scan.valid_chunk_hashes)),
        "invalid_pair_ids": list(scan.invalid_pair_ids),
        "invalid_files": list(scan.invalid_files),
    }
    return add_content_hash(base)


def validate_checkpoint(context: CampaignContext, value: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "campaign_id",
        "campaign_spec_hash",
        "implementation_commit",
        "implementation_source_hash",
        "counts",
        "ordered_valid_chunk_hashes_hash",
        "valid_chunk_hashes",
        "valid_pair_ids",
        "invalid_pair_ids",
        "invalid_files",
        "content_hash",
    }
    if set(value) != required or value.get("schema_version") != CHECKPOINT_SCHEMA:
        raise ChunkIntegrityError("Checkpoint schema differs")
    verify_content_hash(value)
    if value["campaign_id"] != context.campaign_id:
        raise ChunkIntegrityError("Checkpoint campaign identity differs")
    if value["campaign_spec_hash"] != context.campaign_spec_hash:
        raise ChunkIntegrityError("Checkpoint specification identity differs")
    if value["implementation_commit"] != context.implementation_commit:
        raise ChunkIntegrityError("Checkpoint implementation commit differs")
    if value["implementation_source_hash"] != context.implementation_source_hash:
        raise ChunkIntegrityError("Checkpoint source identity differs")
    hashes = value["valid_chunk_hashes"]
    if not isinstance(hashes, Mapping):
        raise ChunkIntegrityError("Checkpoint valid-chunk map is malformed")
    pair_ids = list(sorted(hashes))
    if value["valid_pair_ids"] != pair_ids:
        raise ChunkIntegrityError("Checkpoint valid-pair list differs")
    if value["ordered_valid_chunk_hashes_hash"] != canonical_hash(
        [hashes[pair_id] for pair_id in pair_ids]
    ):
        raise ChunkIntegrityError("Checkpoint ordered chunk hash differs")
    if value["counts"]["completed"] != len(pair_ids) + len(value["invalid_pair_ids"]):
        raise ChunkIntegrityError("Checkpoint completed count differs")


def rebuild_checkpoint(
    context: CampaignContext,
    paths: CampaignPaths,
    *,
    failure_hook: FailureHook | None = None,
) -> Mapping[str, Any]:
    with advisory_lock(paths.checkpoint_lock):
        if paths.checkpoint.exists():
            validate_checkpoint(context, _read_json(paths.checkpoint))
        if failure_hook is not None:
            failure_hook("during-checkpoint-reconstruction")
        scan = scan_campaign(context, paths)
        value = checkpoint_value(context, scan)
        atomic_write_json(
            paths.checkpoint,
            value,
            validator=lambda item: validate_checkpoint(context, item),
            failure_hook=failure_hook,
        )
    return value


def update_checkpoint_after_chunk(
    context: CampaignContext,
    paths: CampaignPaths,
    pair_id: str,
    *,
    failure_hook: FailureHook | None = None,
) -> Mapping[str, Any]:
    """Atomically credit one final chunk without rescanning prior scientific results."""

    with advisory_lock(paths.checkpoint_lock):
        if paths.checkpoint.exists():
            previous = _read_json(paths.checkpoint)
            validate_checkpoint(context, previous)
            valid = dict(previous["valid_chunk_hashes"])
            invalid_pairs = set(previous["invalid_pair_ids"])
            invalid_files = tuple(previous["invalid_files"])
        else:
            recovered = scan_campaign(context, paths)
            if not recovered.integrity_ok:
                raise ChunkIntegrityError("Cannot initialize checkpoint from corrupt chunks")
            valid = dict(recovered.valid_chunk_hashes)
            invalid_pairs = set(recovered.invalid_pair_ids)
            invalid_files = recovered.invalid_files
        chunk = load_pair_chunk(
            context,
            pair_chunk_path(paths, pair_id),
            expected_pair_id=pair_id,
        )
        if chunk["validity_status"] == "VALID":
            valid[pair_id] = str(chunk["content_hash"])
            invalid_pairs.discard(pair_id)
        else:
            valid.pop(pair_id, None)
            invalid_pairs.add(pair_id)
        expected = {context.config.pair_id(index) for index in range(context.config.pair_count)}
        completed = set(valid) | invalid_pairs
        temporary = (
            tuple(sorted(path.name for path in paths.chunks.glob(".*.tmp")))
            if paths.chunks.exists()
            else ()
        )
        scan = CampaignScan(
            valid_chunk_hashes=dict(sorted(valid.items())),
            invalid_pair_ids=tuple(sorted(invalid_pairs)),
            invalid_files=tuple(sorted(invalid_files)),
            duplicate_pair_ids=(),
            missing_pair_ids=tuple(sorted(expected - completed)),
            temporary_files=temporary,
        )
        value = checkpoint_value(context, scan)
        atomic_write_json(
            paths.checkpoint,
            value,
            validator=lambda item: validate_checkpoint(context, item),
            failure_hook=failure_hook,
        )
        return value


def publish_pair_chunk(
    context: CampaignContext,
    paths: CampaignPaths,
    pair_id: str,
    *,
    computer: PairComputer = run_pair,
    failure_hook: FailureHook | None = None,
    refresh_checkpoint: bool = True,
) -> str:
    validate_pair_id(context.config, pair_id)
    final = pair_chunk_path(paths, pair_id)
    lock = paths.locks / f"{pair_id}.lock"
    if failure_hook is not None:
        failure_hook("before-chunk-execution")
    status = "resumed"
    with advisory_lock(lock):
        if final.exists():
            load_pair_chunk(context, final, expected_pair_id=pair_id)
        else:
            if failure_hook is not None:
                failure_hook("during-computation")
            chunk = compute_pair_chunk(context, pair_id, computer=computer)
            atomic_write_json(
                final,
                chunk,
                validator=lambda item: validate_pair_chunk(
                    context, item, expected_pair_id=pair_id
                ),
                failure_hook=failure_hook,
            )
            status = "newly_executed"
    if status == "newly_executed" and failure_hook is not None:
        failure_hook("after-chunk-publication-before-checkpoint")
    if refresh_checkpoint:
        update_checkpoint_after_chunk(
            context,
            paths,
            pair_id,
            failure_hook=failure_hook,
        )
    return status


def completion_manifest_value(
    context: CampaignContext,
    scan: CampaignScan,
) -> dict[str, Any]:
    if not scan.integrity_ok:
        raise CampaignIncompleteError("Campaign contains corrupt or duplicate chunks")
    if scan.invalid_pair_ids:
        raise CampaignIncompleteError("Campaign contains invalid completed scientific chunks")
    if scan.missing_pair_ids:
        raise CampaignIncompleteError("Campaign is missing required matched pairs")
    if len(scan.valid_chunk_hashes) != context.config.pair_count:
        raise CampaignIncompleteError("Campaign valid-pair count differs")
    ordered = [
        {"pair_id": pair_id, "chunk_hash": scan.valid_chunk_hashes[pair_id]}
        for pair_id in sorted(scan.valid_chunk_hashes)
    ]
    base = {
        "schema_version": COMPLETION_MANIFEST_SCHEMA,
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "expected_pair_count": context.config.pair_count,
        "valid_pair_count": len(ordered),
        "invalid_pair_count": 0,
        "missing_pair_count": 0,
        "duplicate_pair_count": 0,
        "interrupted_temporary_file_count": len(scan.temporary_files),
        "ordered_chunks": ordered,
        "ordered_ensemble_hash": canonical_hash(ordered),
    }
    return add_content_hash(base)


def validate_completion_manifest(
    context: CampaignContext,
    value: Mapping[str, Any],
    *,
    paths: CampaignPaths | None = None,
) -> None:
    required = {
        "schema_version",
        "campaign_id",
        "campaign_spec_hash",
        "implementation_commit",
        "implementation_source_hash",
        "expected_pair_count",
        "valid_pair_count",
        "invalid_pair_count",
        "missing_pair_count",
        "duplicate_pair_count",
        "interrupted_temporary_file_count",
        "ordered_chunks",
        "ordered_ensemble_hash",
        "content_hash",
    }
    if set(value) != required or value.get("schema_version") != COMPLETION_MANIFEST_SCHEMA:
        raise ChunkIntegrityError("Completion manifest schema differs")
    verify_content_hash(value)
    if value["campaign_id"] != context.campaign_id:
        raise ChunkIntegrityError("Completion campaign identity differs")
    if value["campaign_spec_hash"] != context.campaign_spec_hash:
        raise ChunkIntegrityError("Completion specification identity differs")
    if value["implementation_commit"] != context.implementation_commit:
        raise ChunkIntegrityError("Completion implementation commit differs")
    if value["implementation_source_hash"] != context.implementation_source_hash:
        raise ChunkIntegrityError("Completion source identity differs")
    if value["expected_pair_count"] != context.config.pair_count:
        raise ChunkIntegrityError("Completion expected-pair count differs")
    if value["valid_pair_count"] != context.config.pair_count:
        raise ChunkIntegrityError("Completion valid-pair count differs")
    if any(value[key] != 0 for key in ("invalid_pair_count", "missing_pair_count", "duplicate_pair_count")):
        raise ChunkIntegrityError("Completion manifest credits an incomplete campaign")
    ordered = value["ordered_chunks"]
    expected_ids = [context.config.pair_id(index) for index in range(context.config.pair_count)]
    if [item["pair_id"] for item in ordered] != expected_ids:
        raise ChunkIntegrityError("Completion manifest pair order or identities differ")
    if len({item["pair_id"] for item in ordered}) != context.config.pair_count:
        raise ChunkIntegrityError("Completion manifest contains duplicate pair identities")
    if value["ordered_ensemble_hash"] != canonical_hash(ordered):
        raise ChunkIntegrityError("Completion ensemble hash differs")
    if paths is not None:
        scan = scan_campaign(context, paths)
        expected = completion_manifest_value(context, scan)
        if value != expected:
            raise ChunkIntegrityError("Completion manifest differs from current chunks")


def publish_completion_manifest(
    context: CampaignContext,
    paths: CampaignPaths,
) -> Mapping[str, Any]:
    value = completion_manifest_value(context, scan_campaign(context, paths))
    if paths.completion_manifest.exists():
        existing = _read_json(paths.completion_manifest)
        validate_completion_manifest(context, existing, paths=paths)
        if existing != value:
            raise ChunkIntegrityError("Existing completion manifest differs")
        return existing
    atomic_write_json(
        paths.completion_manifest,
        value,
        validator=lambda item: validate_completion_manifest(context, item, paths=paths),
    )
    return value


def validate_execution_authorization(
    context: CampaignContext,
    value: Mapping[str, Any],
) -> None:
    expected = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "authorization_id": "gate11-primary-execution-v1",
        "authorized": True,
        "scope": "RUN_3000_MATCHED_PAIRS",
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "pair_count": 3000,
    }
    if value != expected:
        raise Gate11ProtocolError("Primary execution authorization is absent or mismatched")


class InvocationJournal:
    def __init__(
        self,
        context: CampaignContext,
        paths: CampaignPaths,
        invocation_id: str,
        preexisting: Sequence[str],
        interrupted: Sequence[str],
    ) -> None:
        if not invocation_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in invocation_id):
            raise Gate11ProtocolError("Invocation ID is not a bounded simulator-style ID")
        self.context = context
        self.path = paths.journals / f"{invocation_id}.json"
        if self.path.exists():
            raise ChunkIntegrityError("Invocation journal identity already exists")
        self._mutex = threading.Lock()
        self._value: dict[str, Any] = {
            "schema_version": INVOCATION_JOURNAL_SCHEMA,
            "invocation_id": invocation_id,
            "campaign_id": context.campaign_id,
            "campaign_spec_hash": context.campaign_spec_hash,
            "preexisting_valid": list(sorted(preexisting)),
            "newly_computed": [],
            "resumed": list(sorted(preexisting)),
            "interrupted": list(sorted(interrupted)),
            "skipped": [],
            "failed": [],
            "recomputed": [],
            "in_progress": [],
        }
        self._publish()

    def _publish(self) -> None:
        atomic_write_json(self.path, self._value)

    def record(self, category: str, pair_id: str) -> None:
        if category not in self._value or not isinstance(self._value[category], list):
            raise Gate11ProtocolError("Unknown invocation journal category")
        with self._mutex:
            for key in (
                "newly_computed",
                "resumed",
                "interrupted",
                "skipped",
                "failed",
                "recomputed",
                "in_progress",
            ):
                if pair_id in self._value[key]:
                    self._value[key].remove(pair_id)
            self._value[category].append(pair_id)
            self._value[category].sort()
            self._publish()


def run_campaign(
    context: CampaignContext,
    paths: CampaignPaths,
    *,
    worker_count: int,
    invocation_id: str,
    authorization: Mapping[str, Any] | None = None,
    computer: PairComputer = run_pair,
) -> Mapping[str, Any]:
    if worker_count <= 0:
        raise Gate11ProtocolError("Worker count must be positive")
    if context.config.campaign_namespace == "primary":
        if authorization is None:
            raise Gate11ProtocolError("Primary execution requires explicit authorization")
        validate_execution_authorization(context, authorization)
    initial = scan_campaign(context, paths)
    if not initial.integrity_ok or initial.invalid_pair_ids:
        raise ChunkIntegrityError("Campaign cannot resume across invalid or corrupt chunks")
    rebuild_checkpoint(context, paths)
    journal = InvocationJournal(
        context,
        paths,
        invocation_id,
        tuple(initial.valid_chunk_hashes),
        tuple(
            pair_id
            for pair_id in (
                context.config.pair_id(index)
                for index in range(context.config.pair_count)
            )
            if any(
                filename.startswith(f".{pair_id}.")
                for filename in initial.temporary_files
            )
        ),
    )
    pending = list(initial.missing_pair_ids)

    def execute(pair_id: str) -> tuple[str, str]:
        journal.record("in_progress", pair_id)
        try:
            status = publish_pair_chunk(
                context,
                paths,
                pair_id,
                computer=computer,
                refresh_checkpoint=True,
            )
        except BaseException:
            journal.record("failed", pair_id)
            raise
        journal.record("newly_computed" if status == "newly_executed" else "resumed", pair_id)
        return pair_id, status

    if worker_count == 1:
        statuses = [execute(pair_id) for pair_id in pending]
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            statuses = list(executor.map(execute, pending))
    final_scan = scan_campaign(context, paths)
    rebuilt = rebuild_checkpoint(context, paths)
    return {
        "campaign_id": context.campaign_id,
        "completed": final_scan.completed_count,
        "pending": final_scan.pending_count,
        "invalid": final_scan.invalid_count,
        "resumed": len(initial.valid_chunk_hashes)
        + sum(status == "resumed" for _, status in statuses),
        "newly_executed": sum(status == "newly_executed" for _, status in statuses),
        "interrupted": len(final_scan.temporary_files),
        "recomputed": 0,
        "integrity_status": "PASS" if final_scan.integrity_ok else "FAIL",
        "checkpoint_hash": rebuilt["content_hash"],
    }


def load_json_object(path: Path) -> Mapping[str, Any]:
    """Read an operator-owned manifest or authorization object."""

    return _read_json(path)


def canonical_object_sha256(value: Mapping[str, Any]) -> str:
    import hashlib

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
