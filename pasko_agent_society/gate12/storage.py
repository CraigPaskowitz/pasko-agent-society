"""Atomic, resumable, hash-verifiable Gate 1.2 suite storage."""

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

from ..canonical import canonical_hash
from .manifest import AUTHORIZATION_SCHEMA, SuiteSpec
from .protocol import (
    _authorized_alternate_cluster,
    _authorized_standard_pair,
    _production_execution_token,
    run_fixture_alternate_cluster,
    run_fixture_standard_pair,
    validate_alternate_cluster_result,
    validate_standard_pair_result,
)
from .registry import (
    CHECKPOINT_SCHEMA,
    CLUSTER_CHUNK_SCHEMA,
    COMPLETION_SCHEMA,
    PAIR_CHUNK_SCHEMA,
    SUITE_CAMPAIGN_ID,
    SUITE_COMPLETION_SCHEMA,
    AlternateTopologyConfig,
    Gate12InvariantError,
    Gate12ProtocolError,
    StandardConfig,
    alternate_topology_config,
    exact_replication_config,
    fixture_alternate_config,
    fixture_standard_config,
    robustness_config,
    ROBUSTNESS_CELL_IDS,
)


INVOCATION_JOURNAL_SCHEMA = "gate12-invocation-journal-v1"
FailureHook = Callable[[str], None]
UnitComputer = Callable[[StandardConfig | AlternateTopologyConfig, str], Mapping[str, Any]]


class ChunkIntegrityError(RuntimeError):
    """A Gate 1.2 artifact cannot be trusted."""


class CampaignIncompleteError(RuntimeError):
    """A Gate 1.2 subcampaign or suite is incomplete or invalid."""


@dataclass(frozen=True)
class SubcampaignContext:
    suite_id: str
    suite_spec_hash: str
    implementation_commit: str
    implementation_source_hash: str
    config: StandardConfig | AlternateTopologyConfig

    @property
    def subcampaign_id(self) -> str:
        if isinstance(self.config, StandardConfig) and self.config.cell_id:
            return f"{self.config.campaign_id}:{self.config.cell_id}"
        return self.config.campaign_id

    @property
    def unit_kind(self) -> str:
        return "cluster" if isinstance(self.config, AlternateTopologyConfig) else "pair"

    @property
    def expected_unit_ids(self) -> tuple[str, ...]:
        return tuple(self.config.unit_id(index) for index in range(self.config.unit_count))

    @property
    def is_production(self) -> bool:
        return self.config.is_production


def production_contexts(spec: SuiteSpec) -> tuple[SubcampaignContext, ...]:
    if spec.implementation_status != "CERTIFIED_CANDIDATE":
        raise Gate12ProtocolError("Gate 1.2 implementation is not a certified candidate")
    configs: list[StandardConfig | AlternateTopologyConfig] = [exact_replication_config()]
    configs.extend(robustness_config(cell_id) for cell_id in ROBUSTNESS_CELL_IDS)
    configs.append(alternate_topology_config())
    return tuple(
        SubcampaignContext(
            suite_id=SUITE_CAMPAIGN_ID,
            suite_spec_hash=spec.spec_hash,
            implementation_commit=spec.implementation_commit,
            implementation_source_hash=spec.implementation_source_hash,
            config=config,
        )
        for config in configs
    )


def fixture_context(
    config: StandardConfig | AlternateTopologyConfig | None = None,
) -> SubcampaignContext:
    selected = config or fixture_standard_config()
    if selected.is_production:
        raise Gate12ProtocolError("Fixture context requires a fixture namespace")
    return SubcampaignContext(
        suite_id="gate12-fixture-suite-v1",
        suite_spec_hash=canonical_hash({"fixture_config": selected}),
        implementation_commit="fixture-implementation",
        implementation_source_hash=canonical_hash("gate12-fixture-source"),
        config=selected,
    )


def fixture_suite_contexts() -> tuple[SubcampaignContext, ...]:
    return (
        fixture_context(fixture_standard_config()),
        fixture_context(fixture_alternate_config()),
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


def paths_for_context(repository_root: Path, spec: SuiteSpec, context: SubcampaignContext) -> CampaignPaths:
    relative = spec.artifact_root
    if relative.is_absolute() or ".." in relative.parts:
        raise Gate12ProtocolError("Gate 1.2 artifact root is not repository-relative")
    base = repository_root / Path(*relative.parts)
    config = context.config
    if isinstance(config, AlternateTopologyConfig):
        return CampaignPaths(base / "alternate-topology")
    if config.cell_id is None:
        return CampaignPaths(base / "exact-replication")
    return CampaignPaths(base / "standard-robustness" / config.cell_id)


def suite_completion_path(repository_root: Path, spec: SuiteSpec) -> Path:
    relative = spec.artifact_root
    return repository_root / Path(*relative.parts) / "suite-completion-manifest.json"


def suite_analysis_path(repository_root: Path, spec: SuiteSpec) -> Path:
    relative = spec.artifact_root
    return repository_root / Path(*relative.parts) / "gate1_2-confirmatory-analysis.json"


def _identity_without_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "content_hash"}


def add_content_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    if "content_hash" in value:
        raise Gate12ProtocolError("Content hash must not be caller-supplied")
    output = dict(value)
    output["content_hash"] = canonical_hash(output)
    return output


def verify_content_hash(value: Mapping[str, Any]) -> None:
    if value.get("content_hash") != canonical_hash(_identity_without_hash(value)):
        raise ChunkIntegrityError("Canonical content hash differs")


def _unit_id(context: SubcampaignContext, result: Mapping[str, Any]) -> str:
    return str(result.get("unit_id", ""))


def validate_unit_id(context: SubcampaignContext, unit_id: str) -> None:
    suffix = unit_id.rsplit("-", 1)[-1]
    if len(suffix) != 4 or not suffix.isdigit():
        raise Gate12ProtocolError("Unit identity is malformed")
    index = int(suffix)
    if index >= context.config.unit_count or context.config.unit_id(index) != unit_id:
        raise Gate12ProtocolError("Unit identity is outside the subcampaign")


def build_unit_chunk(
    context: SubcampaignContext,
    unit_id: str,
    result: Mapping[str, Any] | None,
    *,
    invalid_reason: str | None = None,
) -> dict[str, Any]:
    validate_unit_id(context, unit_id)
    if (result is None) == (invalid_reason is None):
        raise Gate12ProtocolError("A unit chunk must be valid or explicitly invalid")
    schema = CLUSTER_CHUNK_SCHEMA if context.unit_kind == "cluster" else PAIR_CHUNK_SCHEMA
    base = {
        "schema_version": schema,
        "suite_id": context.suite_id,
        "suite_spec_hash": context.suite_spec_hash,
        "subcampaign_id": context.subcampaign_id,
        "cell_id": context.config.cell_id,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "unit_kind": context.unit_kind,
        "unit_id": unit_id,
        "validity_status": "VALID" if result is not None else "SIMULATOR_INVARIANT_FAILURE",
        "unit_result": result,
        "invalid_reason": invalid_reason,
    }
    chunk = add_content_hash(base)
    validate_unit_chunk(context, chunk, expected_unit_id=unit_id)
    return chunk


def _fixture_computer(context: SubcampaignContext) -> UnitComputer:
    if isinstance(context.config, AlternateTopologyConfig):
        return run_fixture_alternate_cluster
    return run_fixture_standard_pair


def _production_computer(context: SubcampaignContext) -> UnitComputer:
    token = _production_execution_token()
    if isinstance(context.config, AlternateTopologyConfig):
        return lambda config, unit_id: _authorized_alternate_cluster(config, unit_id, token)
    return lambda config, unit_id: _authorized_standard_pair(config, unit_id, token)


def compute_unit_chunk(
    context: SubcampaignContext,
    unit_id: str,
    *,
    computer: UnitComputer | None = None,
) -> dict[str, Any]:
    selected = computer or (
        _production_computer(context) if context.is_production else _fixture_computer(context)
    )
    try:
        result = selected(context.config, unit_id)
    except Gate12InvariantError as error:
        return build_unit_chunk(context, unit_id, None, invalid_reason=str(error))
    return build_unit_chunk(context, unit_id, result)


def validate_unit_chunk(
    context: SubcampaignContext,
    chunk: Mapping[str, Any],
    *,
    expected_unit_id: str | None = None,
) -> None:
    required = {
        "schema_version",
        "suite_id",
        "suite_spec_hash",
        "subcampaign_id",
        "cell_id",
        "implementation_commit",
        "implementation_source_hash",
        "unit_kind",
        "unit_id",
        "validity_status",
        "unit_result",
        "invalid_reason",
        "content_hash",
    }
    expected_schema = CLUSTER_CHUNK_SCHEMA if context.unit_kind == "cluster" else PAIR_CHUNK_SCHEMA
    if set(chunk) != required or chunk.get("schema_version") != expected_schema:
        raise ChunkIntegrityError("Unit chunk schema differs")
    verify_content_hash(chunk)
    unit_id = str(chunk["unit_id"])
    validate_unit_id(context, unit_id)
    if expected_unit_id is not None and unit_id != expected_unit_id:
        raise ChunkIntegrityError("Unit chunk identity differs from filename")
    identities = {
        "suite_id": context.suite_id,
        "suite_spec_hash": context.suite_spec_hash,
        "subcampaign_id": context.subcampaign_id,
        "cell_id": context.config.cell_id,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "unit_kind": context.unit_kind,
    }
    if any(chunk[key] != expected for key, expected in identities.items()):
        raise ChunkIntegrityError("Unit chunk campaign or implementation identity differs")
    if chunk["validity_status"] == "VALID":
        if chunk["unit_result"] is None or chunk["invalid_reason"] is not None:
            raise ChunkIntegrityError("Valid unit chunk payload is incomplete")
        try:
            if isinstance(context.config, AlternateTopologyConfig):
                validate_alternate_cluster_result(context.config, chunk["unit_result"])
            else:
                validate_standard_pair_result(context.config, chunk["unit_result"])
        except (Gate12InvariantError, Gate12ProtocolError) as error:
            raise ChunkIntegrityError("Valid unit result fails conformance") from error
        if _unit_id(context, chunk["unit_result"]) != unit_id:
            raise ChunkIntegrityError("Unit result identity differs from its chunk")
    elif chunk["validity_status"] == "SIMULATOR_INVARIANT_FAILURE":
        if chunk["unit_result"] is not None or not isinstance(chunk["invalid_reason"], str):
            raise ChunkIntegrityError("Invalid completed unit diagnostic is malformed")
    else:
        raise ChunkIntegrityError("Unknown unit validity status")


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_json(path: Path) -> Mapping[str, Any]:
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
    """Publish a complete object or retain the prior valid state."""

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
        decoded = read_json(temporary)
        if validator is not None:
            validator(decoded)
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
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


def chunk_path(paths: CampaignPaths, unit_id: str) -> Path:
    return paths.chunks / f"{unit_id}.json"


def load_unit_chunk(
    context: SubcampaignContext,
    path: Path,
    *,
    expected_unit_id: str | None = None,
) -> Mapping[str, Any]:
    chunk = read_json(path)
    validate_unit_chunk(context, chunk, expected_unit_id=expected_unit_id)
    return chunk


@dataclass(frozen=True)
class CampaignScan:
    valid_chunk_hashes: Mapping[str, str]
    invalid_unit_ids: tuple[str, ...]
    invalid_files: tuple[str, ...]
    duplicate_unit_ids: tuple[str, ...]
    missing_unit_ids: tuple[str, ...]
    temporary_files: tuple[str, ...]

    @property
    def completed_count(self) -> int:
        return len(self.valid_chunk_hashes) + len(self.invalid_unit_ids)

    @property
    def pending_count(self) -> int:
        return len(self.missing_unit_ids)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_unit_ids) + len(self.invalid_files)

    @property
    def integrity_ok(self) -> bool:
        return not self.invalid_files and not self.duplicate_unit_ids


def scan_campaign(context: SubcampaignContext, paths: CampaignPaths) -> CampaignScan:
    expected = set(context.expected_unit_ids)
    valid: dict[str, str] = {}
    invalid_units: set[str] = set()
    invalid_files: list[str] = []
    seen: Counter[str] = Counter()
    if paths.chunks.exists():
        for path in sorted(paths.chunks.glob("*.json"), key=lambda item: item.name):
            try:
                chunk = read_json(path)
                unit_id = str(chunk.get("unit_id", ""))
                if unit_id:
                    seen[unit_id] += 1
                if unit_id not in expected or path.name != f"{unit_id}.json":
                    raise ChunkIntegrityError("Chunk filename or identity differs")
                validate_unit_chunk(context, chunk, expected_unit_id=unit_id)
                if chunk["validity_status"] == "VALID":
                    valid[unit_id] = str(chunk["content_hash"])
                else:
                    invalid_units.add(unit_id)
            except (ChunkIntegrityError, Gate12InvariantError, Gate12ProtocolError):
                invalid_files.append(path.name)
    duplicates = tuple(sorted(unit_id for unit_id, count in seen.items() if count > 1))
    completed = set(valid) | invalid_units
    temporary = (
        tuple(sorted(path.name for path in paths.chunks.glob(".*.tmp")))
        if paths.chunks.exists()
        else ()
    )
    return CampaignScan(
        valid_chunk_hashes=dict(sorted(valid.items())),
        invalid_unit_ids=tuple(sorted(invalid_units)),
        invalid_files=tuple(sorted(invalid_files)),
        duplicate_unit_ids=duplicates,
        missing_unit_ids=tuple(sorted(expected - completed)),
        temporary_files=temporary,
    )


def operational_status(context: SubcampaignContext, paths: CampaignPaths) -> dict[str, Any]:
    scan = scan_campaign(context, paths)
    checkpoint_hash: str | None = None
    checkpoint_ok = True
    if paths.checkpoint.exists():
        try:
            checkpoint = read_json(paths.checkpoint)
            validate_checkpoint(context, checkpoint)
            checkpoint_hash = str(checkpoint["content_hash"])
        except ChunkIntegrityError:
            checkpoint_ok = False
    return {
        "subcampaign_id": context.subcampaign_id,
        "cell_id": context.config.cell_id,
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


def checkpoint_value(context: SubcampaignContext, scan: CampaignScan) -> dict[str, Any]:
    base = {
        "schema_version": CHECKPOINT_SCHEMA,
        "suite_id": context.suite_id,
        "suite_spec_hash": context.suite_spec_hash,
        "subcampaign_id": context.subcampaign_id,
        "cell_id": context.config.cell_id,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "counts": {
            "completed": scan.completed_count,
            "pending": scan.pending_count,
            "invalid": scan.invalid_count,
            "interrupted_temporary_files": len(scan.temporary_files),
        },
        "ordered_valid_chunk_hashes_hash": canonical_hash(
            [scan.valid_chunk_hashes[unit_id] for unit_id in sorted(scan.valid_chunk_hashes)]
        ),
        "valid_chunk_hashes": dict(sorted(scan.valid_chunk_hashes.items())),
        "valid_unit_ids": list(sorted(scan.valid_chunk_hashes)),
        "invalid_unit_ids": list(scan.invalid_unit_ids),
        "invalid_files": list(scan.invalid_files),
    }
    return add_content_hash(base)


def validate_checkpoint(context: SubcampaignContext, value: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "suite_id",
        "suite_spec_hash",
        "subcampaign_id",
        "cell_id",
        "implementation_commit",
        "implementation_source_hash",
        "counts",
        "ordered_valid_chunk_hashes_hash",
        "valid_chunk_hashes",
        "valid_unit_ids",
        "invalid_unit_ids",
        "invalid_files",
        "content_hash",
    }
    if set(value) != required or value.get("schema_version") != CHECKPOINT_SCHEMA:
        raise ChunkIntegrityError("Checkpoint schema differs")
    verify_content_hash(value)
    identities = {
        "suite_id": context.suite_id,
        "suite_spec_hash": context.suite_spec_hash,
        "subcampaign_id": context.subcampaign_id,
        "cell_id": context.config.cell_id,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
    }
    if any(value[key] != expected for key, expected in identities.items()):
        raise ChunkIntegrityError("Checkpoint identity differs")
    hashes = value["valid_chunk_hashes"]
    if not isinstance(hashes, Mapping):
        raise ChunkIntegrityError("Checkpoint valid-chunk map is malformed")
    unit_ids = sorted(hashes)
    if value["valid_unit_ids"] != unit_ids:
        raise ChunkIntegrityError("Checkpoint valid-unit list differs")
    if value["ordered_valid_chunk_hashes_hash"] != canonical_hash(
        [hashes[unit_id] for unit_id in unit_ids]
    ):
        raise ChunkIntegrityError("Checkpoint ordered hash differs")
    if value["counts"]["completed"] != len(unit_ids) + len(value["invalid_unit_ids"]):
        raise ChunkIntegrityError("Checkpoint completed count differs")


def rebuild_checkpoint(
    context: SubcampaignContext,
    paths: CampaignPaths,
    *,
    failure_hook: FailureHook | None = None,
) -> Mapping[str, Any]:
    with advisory_lock(paths.checkpoint_lock):
        if paths.checkpoint.exists():
            validate_checkpoint(context, read_json(paths.checkpoint))
        if failure_hook is not None:
            failure_hook("during-checkpoint-reconstruction")
        value = checkpoint_value(context, scan_campaign(context, paths))
        atomic_write_json(
            paths.checkpoint,
            value,
            validator=lambda item: validate_checkpoint(context, item),
            failure_hook=failure_hook,
        )
        return value


def update_checkpoint_after_chunk(
    context: SubcampaignContext,
    paths: CampaignPaths,
    unit_id: str,
    *,
    failure_hook: FailureHook | None = None,
) -> Mapping[str, Any]:
    with advisory_lock(paths.checkpoint_lock):
        if paths.checkpoint.exists():
            previous = read_json(paths.checkpoint)
            validate_checkpoint(context, previous)
            valid = dict(previous["valid_chunk_hashes"])
            invalid = set(previous["invalid_unit_ids"])
            invalid_files = tuple(previous["invalid_files"])
        else:
            recovered = scan_campaign(context, paths)
            if not recovered.integrity_ok:
                raise ChunkIntegrityError("Cannot initialize checkpoint from corrupt chunks")
            valid = dict(recovered.valid_chunk_hashes)
            invalid = set(recovered.invalid_unit_ids)
            invalid_files = recovered.invalid_files
        chunk = load_unit_chunk(context, chunk_path(paths, unit_id), expected_unit_id=unit_id)
        if chunk["validity_status"] == "VALID":
            valid[unit_id] = str(chunk["content_hash"])
            invalid.discard(unit_id)
        else:
            valid.pop(unit_id, None)
            invalid.add(unit_id)
        completed = set(valid) | invalid
        expected = set(context.expected_unit_ids)
        temporary = (
            tuple(sorted(path.name for path in paths.chunks.glob(".*.tmp")))
            if paths.chunks.exists()
            else ()
        )
        scan = CampaignScan(
            valid_chunk_hashes=dict(sorted(valid.items())),
            invalid_unit_ids=tuple(sorted(invalid)),
            invalid_files=tuple(sorted(invalid_files)),
            duplicate_unit_ids=(),
            missing_unit_ids=tuple(sorted(expected - completed)),
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


def publish_unit_chunk(
    context: SubcampaignContext,
    paths: CampaignPaths,
    unit_id: str,
    *,
    computer: UnitComputer | None = None,
    failure_hook: FailureHook | None = None,
    refresh_checkpoint: bool = True,
) -> str:
    validate_unit_id(context, unit_id)
    final = chunk_path(paths, unit_id)
    lock = paths.locks / f"{unit_id}.lock"
    if failure_hook is not None:
        failure_hook("before-chunk-execution")
    status = "resumed"
    with advisory_lock(lock):
        if final.exists():
            load_unit_chunk(context, final, expected_unit_id=unit_id)
        else:
            if failure_hook is not None:
                failure_hook("during-computation")
            chunk = compute_unit_chunk(context, unit_id, computer=computer)
            atomic_write_json(
                final,
                chunk,
                validator=lambda item: validate_unit_chunk(
                    context, item, expected_unit_id=unit_id
                ),
                failure_hook=failure_hook,
            )
            status = "newly_executed"
    if status == "newly_executed" and failure_hook is not None:
        failure_hook("after-chunk-publication-before-checkpoint")
    if refresh_checkpoint:
        update_checkpoint_after_chunk(context, paths, unit_id, failure_hook=failure_hook)
    return status


def completion_manifest_value(
    context: SubcampaignContext, scan: CampaignScan
) -> dict[str, Any]:
    if not scan.integrity_ok:
        raise CampaignIncompleteError("Subcampaign contains corrupt or duplicate chunks")
    if scan.invalid_unit_ids:
        raise CampaignIncompleteError("Subcampaign contains invalid completed units")
    if scan.missing_unit_ids:
        raise CampaignIncompleteError("Subcampaign is missing required units")
    if len(scan.valid_chunk_hashes) != context.config.unit_count:
        raise CampaignIncompleteError("Subcampaign valid-unit count differs")
    ordered = [
        {"unit_id": unit_id, "chunk_hash": scan.valid_chunk_hashes[unit_id]}
        for unit_id in context.expected_unit_ids
    ]
    base = {
        "schema_version": COMPLETION_SCHEMA,
        "suite_id": context.suite_id,
        "suite_spec_hash": context.suite_spec_hash,
        "subcampaign_id": context.subcampaign_id,
        "cell_id": context.config.cell_id,
        "unit_kind": context.unit_kind,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "expected_unit_count": context.config.unit_count,
        "valid_unit_count": len(ordered),
        "invalid_unit_count": 0,
        "missing_unit_count": 0,
        "duplicate_unit_count": 0,
        "interrupted_temporary_file_count": len(scan.temporary_files),
        "ordered_chunks": ordered,
        "ordered_ensemble_hash": canonical_hash(ordered),
    }
    return add_content_hash(base)


def validate_completion_manifest(
    context: SubcampaignContext,
    value: Mapping[str, Any],
    *,
    paths: CampaignPaths | None = None,
) -> None:
    required = {
        "schema_version",
        "suite_id",
        "suite_spec_hash",
        "subcampaign_id",
        "cell_id",
        "unit_kind",
        "implementation_commit",
        "implementation_source_hash",
        "expected_unit_count",
        "valid_unit_count",
        "invalid_unit_count",
        "missing_unit_count",
        "duplicate_unit_count",
        "interrupted_temporary_file_count",
        "ordered_chunks",
        "ordered_ensemble_hash",
        "content_hash",
    }
    if set(value) != required or value.get("schema_version") != COMPLETION_SCHEMA:
        raise ChunkIntegrityError("Completion manifest schema differs")
    verify_content_hash(value)
    identities = {
        "suite_id": context.suite_id,
        "suite_spec_hash": context.suite_spec_hash,
        "subcampaign_id": context.subcampaign_id,
        "cell_id": context.config.cell_id,
        "unit_kind": context.unit_kind,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "expected_unit_count": context.config.unit_count,
        "valid_unit_count": context.config.unit_count,
    }
    if any(value[key] != expected for key, expected in identities.items()):
        raise ChunkIntegrityError("Completion manifest identity or count differs")
    if any(
        value[key] != 0
        for key in ("invalid_unit_count", "missing_unit_count", "duplicate_unit_count")
    ):
        raise ChunkIntegrityError("Completion manifest credits incomplete science")
    ordered = value["ordered_chunks"]
    if [item["unit_id"] for item in ordered] != list(context.expected_unit_ids):
        raise ChunkIntegrityError("Completion unit order or identities differ")
    if len({item["unit_id"] for item in ordered}) != context.config.unit_count:
        raise ChunkIntegrityError("Completion manifest contains duplicate units")
    if value["ordered_ensemble_hash"] != canonical_hash(ordered):
        raise ChunkIntegrityError("Completion ensemble hash differs")
    if paths is not None and value != completion_manifest_value(context, scan_campaign(context, paths)):
        raise ChunkIntegrityError("Completion manifest differs from current chunks")


def publish_completion_manifest(
    context: SubcampaignContext, paths: CampaignPaths
) -> Mapping[str, Any]:
    value = completion_manifest_value(context, scan_campaign(context, paths))
    if paths.completion_manifest.exists():
        existing = read_json(paths.completion_manifest)
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
    contexts: Sequence[SubcampaignContext], value: Mapping[str, Any]
) -> None:
    if not contexts or any(not context.is_production for context in contexts):
        raise Gate12ProtocolError("Execution authorization applies only to production contexts")
    first = contexts[0]
    expected = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "authorization_id": "gate12-full-suite-execution-v1",
        "authorized": True,
        "scope": "RUN_GATE12_14000_UNITS_30000_CONDITIONS",
        "suite_id": first.suite_id,
        "suite_spec_hash": first.suite_spec_hash,
        "implementation_commit": first.implementation_commit,
        "implementation_source_hash": first.implementation_source_hash,
        "independent_units": 14000,
        "condition_runs": 30000,
    }
    if value != expected:
        raise Gate12ProtocolError("Gate 1.2 execution authorization is absent or mismatched")


class InvocationJournal:
    def __init__(
        self,
        context: SubcampaignContext,
        paths: CampaignPaths,
        invocation_id: str,
        preexisting: Sequence[str],
        interrupted: Sequence[str],
    ) -> None:
        if not invocation_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in invocation_id
        ):
            raise Gate12ProtocolError("Invocation ID is not a bounded simulator-style ID")
        self.path = paths.journals / f"{invocation_id}.json"
        if self.path.exists():
            raise ChunkIntegrityError("Invocation journal identity already exists")
        self._mutex = threading.Lock()
        self._value: dict[str, Any] = {
            "schema_version": INVOCATION_JOURNAL_SCHEMA,
            "invocation_id": invocation_id,
            "suite_id": context.suite_id,
            "suite_spec_hash": context.suite_spec_hash,
            "subcampaign_id": context.subcampaign_id,
            "preexisting_valid": sorted(preexisting),
            "newly_computed": [],
            "resumed": sorted(preexisting),
            "interrupted": sorted(interrupted),
            "skipped": [],
            "failed": [],
            "recomputed": [],
            "in_progress": [],
        }
        self._publish()

    def _publish(self) -> None:
        atomic_write_json(self.path, self._value)

    def record(self, category: str, unit_id: str) -> None:
        if category not in self._value or not isinstance(self._value[category], list):
            raise Gate12ProtocolError("Unknown invocation journal category")
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
                if unit_id in self._value[key]:
                    self._value[key].remove(unit_id)
            self._value[category].append(unit_id)
            self._value[category].sort()
            self._publish()


def run_subcampaign(
    context: SubcampaignContext,
    paths: CampaignPaths,
    *,
    worker_count: int,
    invocation_id: str,
    authorization: Mapping[str, Any] | None = None,
    authorization_contexts: Sequence[SubcampaignContext] | None = None,
    computer: UnitComputer | None = None,
) -> Mapping[str, Any]:
    if worker_count <= 0:
        raise Gate12ProtocolError("Worker count must be positive")
    if context.is_production:
        if authorization is None or authorization_contexts is None:
            raise Gate12ProtocolError("Production execution requires explicit authorization")
        validate_execution_authorization(authorization_contexts, authorization)
        if context not in authorization_contexts:
            raise Gate12ProtocolError("Subcampaign is outside the authorized suite")
    initial = scan_campaign(context, paths)
    if not initial.integrity_ok or initial.invalid_unit_ids:
        raise ChunkIntegrityError("Subcampaign cannot resume across invalid or corrupt chunks")
    rebuild_checkpoint(context, paths)
    journal = InvocationJournal(
        context,
        paths,
        invocation_id,
        tuple(initial.valid_chunk_hashes),
        tuple(
            unit_id
            for unit_id in context.expected_unit_ids
            if any(name.startswith(f".{unit_id}.") for name in initial.temporary_files)
        ),
    )

    def execute(unit_id: str) -> tuple[str, str]:
        journal.record("in_progress", unit_id)
        try:
            status = publish_unit_chunk(context, paths, unit_id, computer=computer)
        except BaseException:
            journal.record("failed", unit_id)
            raise
        journal.record("newly_computed" if status == "newly_executed" else "resumed", unit_id)
        return unit_id, status

    pending = list(initial.missing_unit_ids)
    if worker_count == 1:
        statuses = [execute(unit_id) for unit_id in pending]
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            statuses = list(executor.map(execute, pending))
    final_scan = scan_campaign(context, paths)
    rebuilt = rebuild_checkpoint(context, paths)
    return {
        "subcampaign_id": context.subcampaign_id,
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


def suite_completion_value(
    contexts: Sequence[SubcampaignContext],
    paths_by_id: Mapping[str, CampaignPaths],
) -> dict[str, Any]:
    production = bool(contexts) and all(context.is_production for context in contexts)
    expected_subcampaigns = 12 if production else len(contexts)
    if (
        not contexts
        or len(contexts) != expected_subcampaigns
        or len({context.subcampaign_id for context in contexts}) != expected_subcampaigns
    ):
        raise CampaignIncompleteError("Suite subcampaign registry is incomplete or duplicated")
    completion_records = []
    for context in contexts:
        try:
            paths = paths_by_id[context.subcampaign_id]
        except KeyError as error:
            raise CampaignIncompleteError("Subcampaign path is missing") from error
        if not paths.completion_manifest.exists():
            raise CampaignIncompleteError("Subcampaign completion manifest is missing")
        completion = read_json(paths.completion_manifest)
        validate_completion_manifest(context, completion, paths=paths)
        completion_records.append(
            {
                "subcampaign_id": context.subcampaign_id,
                "cell_id": context.config.cell_id,
                "unit_kind": context.unit_kind,
                "valid_unit_count": completion["valid_unit_count"],
                "completion_manifest_hash": completion["content_hash"],
                "ordered_ensemble_hash": completion["ordered_ensemble_hash"],
            }
        )
    ordered = sorted(completion_records, key=lambda item: item["subcampaign_id"])
    condition_runs = sum(
        context.config.unit_count
        * (
            1 + context.config.realization_count
            if isinstance(context.config, AlternateTopologyConfig)
            else 2
        )
        for context in contexts
    )
    base = {
        "schema_version": SUITE_COMPLETION_SCHEMA,
        "suite_id": contexts[0].suite_id,
        "suite_spec_hash": contexts[0].suite_spec_hash,
        "implementation_commit": contexts[0].implementation_commit,
        "implementation_source_hash": contexts[0].implementation_source_hash,
        "subcampaign_count": expected_subcampaigns,
        "independent_unit_count": sum(item["valid_unit_count"] for item in ordered),
        "condition_run_count": condition_runs,
        "invalid_unit_count": 0,
        "missing_unit_count": 0,
        "duplicate_unit_count": 0,
        "ordered_subcampaigns": ordered,
        "ordered_suite_ensemble_hash": canonical_hash(ordered),
    }
    if production and (
        base["independent_unit_count"] != 14000 or condition_runs != 30000
    ):
        raise CampaignIncompleteError("Gate 1.2 independent-unit total differs")
    return add_content_hash(base)


def validate_suite_completion(
    contexts: Sequence[SubcampaignContext],
    paths_by_id: Mapping[str, CampaignPaths],
    value: Mapping[str, Any],
) -> None:
    expected = suite_completion_value(contexts, paths_by_id)
    if value != expected:
        raise ChunkIntegrityError("Suite completion manifest differs from verified subcampaigns")


def publish_suite_completion(
    contexts: Sequence[SubcampaignContext],
    paths_by_id: Mapping[str, CampaignPaths],
    path: Path,
) -> Mapping[str, Any]:
    value = suite_completion_value(contexts, paths_by_id)
    if path.exists():
        existing = read_json(path)
        validate_suite_completion(contexts, paths_by_id, existing)
        return existing
    atomic_write_json(
        path,
        value,
        validator=lambda item: validate_suite_completion(contexts, paths_by_id, item),
    )
    return value


def verify_suite_completion(
    contexts: Sequence[SubcampaignContext],
    paths_by_id: Mapping[str, CampaignPaths],
    path: Path,
) -> Mapping[str, Any]:
    if not path.exists():
        raise CampaignIncompleteError("Gate 1.2 suite completion manifest is absent")
    value = read_json(path)
    validate_suite_completion(contexts, paths_by_id, value)
    return value


def load_completed_unit_results(
    context: SubcampaignContext, paths: CampaignPaths
) -> list[Mapping[str, Any]]:
    if not paths.completion_manifest.exists():
        raise CampaignIncompleteError("Subcampaign analysis is locked before completion")
    completion = read_json(paths.completion_manifest)
    validate_completion_manifest(context, completion, paths=paths)
    results = []
    for unit_id in context.expected_unit_ids:
        chunk = load_unit_chunk(context, chunk_path(paths, unit_id), expected_unit_id=unit_id)
        if chunk["validity_status"] != "VALID":
            raise CampaignIncompleteError("Invalid unit cannot enter analysis")
        results.append(chunk["unit_result"])
    return results
