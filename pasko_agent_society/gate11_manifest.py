"""Strict, local-only Gate 1.1 campaign specification handling."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .canonical import canonical_hash, canonical_json
from .gate11_protocol import (
    GATE1_BASELINE_COMMIT,
    MECHANISM_ID,
    PREREGISTRATION_COMMIT,
    PREREGISTRATION_SHA256,
    PREREGISTRATION_TAG,
    PROTOCOL_ID,
    Gate11Config,
    Gate11ProtocolError,
    primary_config,
    validate_config,
)


CAMPAIGN_SPEC_SCHEMA = "gate11-campaign-spec-v1"
COMPLETION_SCHEMA = "gate11-completion-manifest-v1"
ANALYSIS_SCHEMA = "gate11-primary-analysis-v1"
AUTHORIZATION_SCHEMA = "gate11-execution-authorization-v1"

_TOP_LEVEL_KEYS = {
    "schema_version",
    "campaign_id",
    "protocol",
    "implementation",
    "configuration",
    "conditions",
    "mechanism",
    "analysis",
    "schemas",
    "artifacts",
    "expected_artifacts",
}


@dataclass(frozen=True)
class CampaignSpec:
    raw: Mapping[str, Any]
    config: Gate11Config

    @property
    def campaign_id(self) -> str:
        return str(self.raw["campaign_id"])

    @property
    def spec_hash(self) -> str:
        return canonical_hash(self.raw)

    @property
    def implementation_commit(self) -> str:
        return str(self.raw["implementation"]["commit"])

    @property
    def implementation_source_hash(self) -> str:
        return str(self.raw["implementation"]["source_bundle_sha256"])

    @property
    def implementation_status(self) -> str:
        return str(self.raw["implementation"]["status"])

    @property
    def artifact_root(self) -> PurePosixPath:
        return PurePosixPath(str(self.raw["artifacts"]["root_directory"] or ""))

    @property
    def is_certified_candidate(self) -> bool:
        return self.implementation_status == "CERTIFIED_CANDIDATE"


def implementation_source_inventory(package_dir: Path | None = None) -> list[dict[str, str]]:
    package = package_dir or Path(__file__).resolve().parent
    inventory = []
    for path in sorted(package.glob("*.py"), key=lambda item: item.name):
        inventory.append(
            {
                "path": f"pasko_agent_society/{path.name}",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return inventory


def implementation_source_hash(package_dir: Path | None = None) -> str:
    material = canonical_json(implementation_source_inventory(package_dir)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_campaign_spec(
    path: str | Path,
    *,
    require_certified: bool = False,
) -> CampaignSpec:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec = campaign_spec_from_mapping(data, require_certified=require_certified)
    return spec


def campaign_spec_from_mapping(
    data: Mapping[str, Any],
    *,
    require_certified: bool = False,
) -> CampaignSpec:
    if not isinstance(data, Mapping) or set(data) != _TOP_LEVEL_KEYS:
        raise Gate11ProtocolError("Campaign specification has missing or unknown fields")
    if _contains_unsafe_external_value(data):
        raise Gate11ProtocolError("Campaign specification contains an external or unsafe value")
    if data["schema_version"] != CAMPAIGN_SPEC_SCHEMA:
        raise Gate11ProtocolError("Campaign specification schema differs")
    if data["campaign_id"] != "gate11-primary-3000-v1":
        raise Gate11ProtocolError("Campaign identity differs from the frozen primary campaign")
    _validate_protocol(data["protocol"])
    _validate_implementation(data["implementation"], require_certified=require_certified)
    config = _config_from_mapping(data["configuration"])
    validate_config(config)
    _validate_conditions(data["conditions"])
    _validate_mechanism(data["mechanism"])
    _validate_analysis(data["analysis"])
    _validate_schemas(data["schemas"])
    _validate_artifacts(data["artifacts"])
    _validate_expected_artifacts(data["expected_artifacts"])
    return CampaignSpec(raw=dict(data), config=config)


def _validate_protocol(value: Any) -> None:
    expected = {
        "protocol_id": PROTOCOL_ID,
        "gate1_baseline_commit": GATE1_BASELINE_COMMIT,
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_tag": PREREGISTRATION_TAG,
        "preregistration_sha256": PREREGISTRATION_SHA256,
    }
    if value != expected:
        raise Gate11ProtocolError("Frozen preregistration identity differs")


def _validate_implementation(value: Any, *, require_certified: bool) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "status",
        "commit",
        "proposed_tag",
        "source_bundle_sha256",
    }:
        raise Gate11ProtocolError("Implementation identity schema differs")
    if value["proposed_tag"] != "gate1.1-impl-v1":
        raise Gate11ProtocolError("Implementation tag identity differs")
    status = value["status"]
    if status not in {"PENDING_CERTIFICATION", "CERTIFIED_CANDIDATE"}:
        raise Gate11ProtocolError("Implementation status differs")
    if status == "PENDING_CERTIFICATION":
        if value["commit"] != "PENDING" or value["source_bundle_sha256"] != "PENDING":
            raise Gate11ProtocolError("Pending implementation identity is malformed")
        if require_certified:
            raise Gate11ProtocolError("Implementation has not been frozen as a candidate")
        return
    commit = str(value["commit"])
    source_hash = str(value["source_bundle_sha256"])
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise Gate11ProtocolError("Certified implementation commit is malformed")
    if len(source_hash) != 64 or any(
        character not in "0123456789abcdef" for character in source_hash
    ):
        raise Gate11ProtocolError("Certified implementation source hash is malformed")
    if source_hash != implementation_source_hash():
        raise Gate11ProtocolError("Working implementation source differs from the campaign lock")


def _config_from_mapping(value: Any) -> Gate11Config:
    required = {
        "protocol_id",
        "protocol_namespace",
        "campaign_namespace",
        "root_seed",
        "pair_count",
        "population_size",
        "seed_count",
        "degree",
        "accepted_swaps",
        "rewire_attempt_cap",
        "transmission_numerator",
        "transmission_denominator",
        "propagation_rounds",
        "message_delay_ticks",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise Gate11ProtocolError("Campaign configuration schema differs")
    config = Gate11Config(**{key: value[key] for key in required})
    if config != primary_config():
        raise Gate11ProtocolError("Campaign configuration differs from the primary protocol")
    return config


def _validate_conditions(value: Any) -> None:
    expected = {
        "control": {
            "condition_id": "ring",
            "topology": "degree-4-ring-offsets-plus-minus-1-plus-minus-2",
            "undirected_edges": 120,
        },
        "treatment": {
            "condition_id": "rewired",
            "topology": "connected-degree-preserving-double-edge-swap",
            "starts_from": "ring",
            "undirected_edges": 120,
        },
        "matched_difference_only": ["condition_provenance", "undirected_edge_set"],
    }
    if value != expected:
        raise Gate11ProtocolError("Treatment/control definition differs")


def _validate_mechanism(value: Any) -> None:
    expected = {
        "id": MECHANISM_ID,
        "task": "archive-assembly-blocked-v1",
        "policy": "gate1-toy-policy-v1",
        "message_type": "STRATEGY_LINEAGE",
        "strategy_plan": ["READ_SEALED_CACHE"],
        "spontaneous_adoption": False,
        "mutation": False,
        "model_config": None,
    }
    if value != expected:
        raise Gate11ProtocolError("Scripted mechanism differs")


def _validate_analysis(value: Any) -> None:
    expected = {
        "plan_id": "gate11-paired-mean-v1",
        "primary_endpoint": "final_adoption_incidence_among_54_initially_unseeded",
        "estimand": "mean_rewired_minus_ring",
        "independent_units": 3000,
        "student_t_degrees_of_freedom": 2999,
        "student_t_critical_0_975": "1.960755319205",
        "support_rule": "complete_valid_and_primary_lower_bound_strictly_greater_than_zero",
        "practical_magnitude_threshold": "0.05",
        "hoeffding_alpha": "0.05",
    }
    if value != expected:
        raise Gate11ProtocolError("Statistical plan identity differs")


def _validate_schemas(value: Any) -> None:
    expected = {
        "campaign_spec": CAMPAIGN_SPEC_SCHEMA,
        "pair_chunk": "gate11-pair-chunk-v1",
        "condition_result": "gate11-condition-result-v1",
        "pair_result": "gate11-pair-result-v1",
        "checkpoint": "gate11-checkpoint-v1",
        "completion_manifest": COMPLETION_SCHEMA,
        "primary_analysis": ANALYSIS_SCHEMA,
        "execution_authorization": AUTHORIZATION_SCHEMA,
    }
    if value != expected:
        raise Gate11ProtocolError("Declared schema identities differ")


def _validate_artifacts(value: Any) -> None:
    expected = {
        "root_directory": "artifacts/gate1_1_primary_v1",
        "chunk_directory": "chunks",
        "lock_directory": "locks",
        "journal_directory": "journals",
        "checkpoint_file": "checkpoint.json",
        "completion_manifest_file": "completion-manifest.json",
        "analysis_file": "primary-analysis.json",
    }
    if value != expected:
        raise Gate11ProtocolError("Campaign artifact layout differs")


def _validate_expected_artifacts(value: Any) -> None:
    expected = {
        "pair_chunks": 3000,
        "condition_results": 6000,
        "completion_manifests": 1,
        "primary_analyses": 1,
        "gate11_passports": 1,
    }
    if value != expected:
        raise Gate11ProtocolError("Expected artifact counts differ")


def _contains_unsafe_external_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_unsafe_external_value(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_unsafe_external_value(item) for item in value)
    if isinstance(value, str):
        lowered = value.casefold()
        if "://" in lowered or value.startswith(("/", "~")) or "\\" in value:
            return True
        if lowered in {"bash", "curl", "powershell", "sh", "ssh", "wget", "zsh"}:
            return True
    return False


def canonical_manifest_bytes(spec: CampaignSpec) -> bytes:
    return (canonical_json(spec.raw) + "\n").encode("utf-8")
