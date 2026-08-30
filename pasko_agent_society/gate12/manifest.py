"""Strict, outcome-free Gate 1.2 suite-manifest handling."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ..canonical import canonical_hash, canonical_json
from .registry import (
    ALL_ROBUSTNESS_CONTRAST_IDS,
    ALTERNATE_CAMPAIGN_ID,
    ANALYSIS_SCHEMA,
    AUTHORIZATION_SCHEMA,
    CHECKPOINT_SCHEMA,
    CLUSTER_CHUNK_SCHEMA,
    CLUSTER_RESULT_SCHEMA,
    COMPLETION_SCHEMA,
    CONDITION_RESULT_SCHEMA,
    EQUIVALENCE_MARGIN,
    EXACT_CAMPAIGN_ID,
    GATE11_RESULT_COMMIT,
    GATE11_RESULT_TAG,
    GATE12_PREREGISTRATION_COMMIT,
    GATE12_PREREGISTRATION_SHA256,
    GATE12_PREREGISTRATION_TAG,
    PAIR_CHUNK_SCHEMA,
    PAIR_RESULT_SCHEMA,
    PRACTICAL_MAGNITUDE_THRESHOLD,
    PROTOCOL_ID,
    PROTOCOL_NAMESPACE,
    ROBUSTNESS_CAMPAIGN_ID,
    ROBUSTNESS_CELL_IDS,
    ROBUSTNESS_FAMILY_SIZE,
    SUITE_CAMPAIGN_ID,
    SUITE_COMPLETION_SCHEMA,
    T_CRITICAL_2999,
    T_CRITICAL_999,
    T_CRITICAL_EQUIV_2999,
    T_CRITICAL_FAMILY_999,
    Gate12ProtocolError,
    alternate_config_mapping,
    alternate_topology_config,
    exact_replication_config,
    robustness_config,
    standard_config_mapping,
)


SUITE_SPEC_SCHEMA = "gate12-suite-spec-v1"
IMPLEMENTATION_TAG = "gate1.2-impl-v1"

GATE11_PREREGISTRATION_COMMIT = "cc1ab868a7401099751030580649e49258654fe2"
GATE11_PREREGISTRATION_TAG = "gate1.1-prereg-v1"
GATE11_PREREGISTRATION_SHA256 = (
    "e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706"
)
GATE11_IMPLEMENTATION_COMMIT = "4c8bb4d3f88a38469a6edcb770b1b0a037a73ae7"
GATE11_IMPLEMENTATION_TAG = "gate1.1-impl-v1"
GATE11_SCIENTIFIC_CODE_COMMIT = "d31c78011abfc164fd3d20125bbe995e4023ee4a"
GATE11_SOURCE_BUNDLE_SHA256 = (
    "c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09"
)
GATE11_CAMPAIGN_HASH = (
    "sha256:76ceaf1e182b5b6ecbe8214a694b4000d47d495165ab025f15112901e71600f2"
)
GATE11_RESULT_REPORT_SHA256 = (
    "7df93c11bcb2e5015112951122cb6e06526d6d976d76bcf04fbd99cbbe00e419"
)
GATE11_PASSPORT_SHA256 = (
    "a61ca9010b732f315b34ac89b57bfd1b340093814bd6161b668e77f4943bc2d7"
)
GATE11_EVIDENCE_INDEX_SHA256 = (
    "648826dadfd52bb6fe572ee3532a23f6266074113768fa7e279f636167d147ba"
)
GATE11_PRIMARY_ANALYSIS_FILE_SHA256 = (
    "7e0731418f74accedd787895dd99e5b0b2243388c5470b18ec45ed361e390248"
)
GATE11_PRIMARY_ANALYSIS_CONTENT_HASH = (
    "sha256:a910f13451e642ca57e81a8b2e1bfa04b9705aabbabe5d63cfde0e7e220a4ca8"
)
GATE11_ESTIMATE = 0.048462962962962965
GATE11_STANDARD_ERROR = 0.002747093557589376
GATE11_SUPPORTED = True


@dataclass(frozen=True)
class SuiteSpec:
    raw: Mapping[str, Any]

    @property
    def spec_hash(self) -> str:
        return canonical_hash(self.raw)

    @property
    def implementation_status(self) -> str:
        return str(self.raw["implementation"]["status"])

    @property
    def implementation_commit(self) -> str:
        return str(self.raw["implementation"]["commit"])

    @property
    def implementation_source_hash(self) -> str:
        return str(self.raw["implementation"]["source_bundle_sha256"])

    @property
    def artifact_root(self) -> PurePosixPath:
        return PurePosixPath(str(self.raw["artifacts"]["root_directory"]))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def implementation_source_inventory(repository_root: Path | None = None) -> list[dict[str, str]]:
    root = repository_root or Path(__file__).resolve().parents[2]
    package = root / "pasko_agent_society"
    paths = list(package.glob("*.py")) + list((package / "gate12").glob("*.py"))
    inventory = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        inventory.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return inventory


def implementation_source_hash(repository_root: Path | None = None) -> str:
    material = canonical_json(implementation_source_inventory(repository_root)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _implementation_mapping(status: str, commit: str, source_hash: str) -> dict[str, Any]:
    return {
        "status": status,
        "commit": commit,
        "proposed_tag": IMPLEMENTATION_TAG,
        "source_bundle_sha256": source_hash,
    }


def _bind_child_spec(value: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(value)
    output["canonical_hash"] = canonical_hash(output)
    return output


def expected_suite_mapping(
    *,
    implementation_status: str = "PENDING_CERTIFICATION",
    implementation_commit: str = "PENDING",
    implementation_source_sha256: str = "PENDING",
) -> dict[str, Any]:
    exact = _bind_child_spec(standard_config_mapping(exact_replication_config()))
    cells = [
        _bind_child_spec(standard_config_mapping(robustness_config(cell_id)))
        for cell_id in ROBUSTNESS_CELL_IDS
    ]
    standard_parent = {
        "campaign_id": ROBUSTNESS_CAMPAIGN_ID,
        "root_seed": 20260901,
        "cell_count": 10,
        "units_per_cell": 1000,
        "condition_runs_per_cell": 2000,
        "cells": cells,
    }
    standard_parent = _bind_child_spec(standard_parent)
    alternate = _bind_child_spec(alternate_config_mapping(alternate_topology_config()))
    return {
        "schema_version": SUITE_SPEC_SCHEMA,
        "suite_id": SUITE_CAMPAIGN_ID,
        "protocol": {
            "protocol_id": PROTOCOL_ID,
            "protocol_namespace": PROTOCOL_NAMESPACE,
            "gate1_2_preregistration": {
                "commit": GATE12_PREREGISTRATION_COMMIT,
                "tag": GATE12_PREREGISTRATION_TAG,
                "document_sha256": GATE12_PREREGISTRATION_SHA256,
            },
            "gate1_1_provenance": {
                "preregistration_commit": GATE11_PREREGISTRATION_COMMIT,
                "preregistration_tag": GATE11_PREREGISTRATION_TAG,
                "preregistration_sha256": GATE11_PREREGISTRATION_SHA256,
                "implementation_commit": GATE11_IMPLEMENTATION_COMMIT,
                "implementation_tag": GATE11_IMPLEMENTATION_TAG,
                "scientific_code_commit": GATE11_SCIENTIFIC_CODE_COMMIT,
                "source_bundle_sha256": GATE11_SOURCE_BUNDLE_SHA256,
                "campaign_hash": GATE11_CAMPAIGN_HASH,
                "result_commit": GATE11_RESULT_COMMIT,
                "result_tag": GATE11_RESULT_TAG,
                "result_report_sha256": GATE11_RESULT_REPORT_SHA256,
                "passport_sha256": GATE11_PASSPORT_SHA256,
                "evidence_index_sha256": GATE11_EVIDENCE_INDEX_SHA256,
                "primary_analysis_file_sha256": GATE11_PRIMARY_ANALYSIS_FILE_SHA256,
                "primary_analysis_content_hash": GATE11_PRIMARY_ANALYSIS_CONTENT_HASH,
            },
        },
        "implementation": _implementation_mapping(
            implementation_status,
            implementation_commit,
            implementation_source_sha256,
        ),
        "campaign_families": {
            "exact_replication": exact,
            "standard_robustness": standard_parent,
            "alternate_topology": alternate,
        },
        "analysis": {
            "primary_replication": {
                "plan_id": "gate12-exact-replication-paired-mean-v1",
                "endpoint": "final_adoption_incidence_among_initially_unseeded",
                "estimand": "mean_rewired_minus_ring",
                "independent_units": 3000,
                "degrees_of_freedom": 2999,
                "t_critical_0_975": f"{T_CRITICAL_2999:.12f}",
                "support_rule": "complete_valid_and_lower_bound_strictly_greater_than_zero",
                "practical_magnitude_threshold": f"{PRACTICAL_MAGNITUDE_THRESHOLD:.2f}",
                "hoeffding_alpha": "0.05",
            },
            "cross_gate_magnitude": {
                "plan_id": "gate12-gate11-magnitude-equivalence-v1",
                "gate1_1_estimate": repr(GATE11_ESTIMATE),
                "gate1_1_standard_error": repr(GATE11_STANDARD_ERROR),
                "gate1_1_supported": GATE11_SUPPORTED,
                "equivalence_margin": f"{EQUIVALENCE_MARGIN:.2f}",
                "degrees_of_freedom": 2999,
                "t_critical_0_95": f"{T_CRITICAL_EQUIV_2999:.12f}",
            },
            "robustness_family": {
                "plan_id": "gate12-robustness-bonferroni-v1",
                "contrast_ids": list(ALL_ROBUSTNESS_CONTRAST_IDS),
                "family_size": ROBUSTNESS_FAMILY_SIZE,
                "independent_units_per_contrast": 1000,
                "degrees_of_freedom": 999,
                "unadjusted_t_critical_0_975": f"{T_CRITICAL_999:.12f}",
                "family_t_critical": f"{T_CRITICAL_FAMILY_999:.12f}",
                "strong_robustness_rule": "every_simultaneous_lower_bound_strictly_greater_than_zero",
                "directional_stability_rule": "every_point_estimate_strictly_greater_than_zero",
                "strong_reversal_rule": "any_simultaneous_upper_bound_strictly_less_than_zero",
            },
            "joint_classification": {
                "plan_id": "gate12-joint-classification-v1",
                "ordered_labels": [
                    "invalid/inconclusive",
                    "replicated and robust",
                    "replicated but specification-sensitive",
                    "replicated; robustness directionally consistent but imprecise",
                    "directionally consistent but imprecise",
                    "failed replication",
                    "heterogeneous/inconclusive",
                    "concordant non-support",
                ],
            },
        },
        "schemas": {
            "suite_spec": SUITE_SPEC_SCHEMA,
            "pair_chunk": PAIR_CHUNK_SCHEMA,
            "cluster_chunk": CLUSTER_CHUNK_SCHEMA,
            "condition_result": CONDITION_RESULT_SCHEMA,
            "pair_result": PAIR_RESULT_SCHEMA,
            "cluster_result": CLUSTER_RESULT_SCHEMA,
            "checkpoint": CHECKPOINT_SCHEMA,
            "completion_manifest": COMPLETION_SCHEMA,
            "suite_completion": SUITE_COMPLETION_SCHEMA,
            "confirmatory_analysis": ANALYSIS_SCHEMA,
            "execution_authorization": AUTHORIZATION_SCHEMA,
        },
        "artifacts": {
            "root_directory": "artifacts/gate1_2_v1",
            "exact_replication_directory": "exact-replication",
            "standard_robustness_directory": "standard-robustness",
            "alternate_topology_directory": "alternate-topology",
            "chunk_directory": "chunks",
            "lock_directory": "locks",
            "journal_directory": "journals",
            "checkpoint_file": "checkpoint.json",
            "completion_manifest_file": "completion-manifest.json",
            "suite_completion_file": "suite-completion-manifest.json",
            "analysis_file": "gate1_2-confirmatory-analysis.json",
        },
        "expected_artifacts": {
            "independent_units": 14000,
            "condition_runs": 30000,
            "scripted_agent_runs": 1800000,
            "pair_chunks": 13000,
            "cluster_chunks": 1000,
            "subcampaign_completion_manifests": 12,
            "suite_completion_manifests": 1,
            "confirmatory_analyses": 1,
            "gate12_passports": 1,
        },
    }


def _unsafe(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_unsafe(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_unsafe(item) for item in value)
    if isinstance(value, str):
        lowered = value.casefold()
        if "://" in lowered or value.startswith(("/", "~")) or "\\" in value:
            return True
        if lowered in {"bash", "curl", "powershell", "sh", "ssh", "wget", "zsh"}:
            return True
    return False


def suite_spec_from_mapping(
    data: Mapping[str, Any], *, require_certified: bool = False
) -> SuiteSpec:
    if not isinstance(data, Mapping) or _unsafe(data):
        raise Gate12ProtocolError("Suite manifest is malformed or contains an unsafe value")
    implementation = data.get("implementation")
    if not isinstance(implementation, Mapping):
        raise Gate12ProtocolError("Suite implementation identity is malformed")
    status = implementation.get("status")
    commit = str(implementation.get("commit", ""))
    source_hash = str(implementation.get("source_bundle_sha256", ""))
    if status == "PENDING_CERTIFICATION":
        if commit != "PENDING" or source_hash != "PENDING" or require_certified:
            raise Gate12ProtocolError("Pending implementation identity is invalid")
    elif status == "CERTIFIED_CANDIDATE":
        if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
            raise Gate12ProtocolError("Certified implementation commit is malformed")
        if len(source_hash) != 64 or any(
            character not in "0123456789abcdef" for character in source_hash
        ):
            raise Gate12ProtocolError("Certified source hash is malformed")
        if source_hash != implementation_source_hash():
            raise Gate12ProtocolError("Working source differs from the Gate 1.2 source lock")
    else:
        raise Gate12ProtocolError("Unknown implementation status")
    expected = expected_suite_mapping(
        implementation_status=str(status),
        implementation_commit=commit,
        implementation_source_sha256=source_hash,
    )
    if data != expected:
        raise Gate12ProtocolError("Suite manifest differs from the frozen Gate 1.2 protocol")
    return SuiteSpec(raw=dict(data))


def load_suite_spec(path: str | Path, *, require_certified: bool = False) -> SuiteSpec:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise Gate12ProtocolError("Suite manifest root is not an object")
    return suite_spec_from_mapping(value, require_certified=require_certified)


def canonical_manifest_bytes(spec: SuiteSpec) -> bytes:
    return (canonical_json(spec.raw) + "\n").encode("utf-8")
