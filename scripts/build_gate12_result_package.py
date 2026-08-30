#!/usr/bin/env python3
"""Build the compact Gate 1.2 result package from verified canonical artifacts.

This script never executes a scientific unit or reruns the confirmatory analysis.
It copies frozen manifests, derives preregistered/descriptive summaries from the
already verified chunks, and optionally indexes the resulting public package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "artifacts" / "gate1_2_v1"
RESULTS = ROOT / "results" / "gate1_2"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.canonical import canonical_hash  # noqa: E402


BUILT_AT_UTC = "2026-08-30T23:01:57Z"
EXPECTED_SUITE_HASH = (
    "sha256:c111cd3bad274cd83b54298545112d513e5c216d391204b0b6bd56f68ebd332f"
)
EXPECTED_ANALYSIS_HASH = (
    "sha256:f1ab741de5b57e9ccaaab437299992538baa549d1bb2de4c59a5cd7c1220e7f0"
)

CELL_IDS = (
    "p-1-of-8",
    "p-3-of-8",
    "seeds-3",
    "seeds-12",
    "rounds-4",
    "rounds-12",
    "swaps-360",
    "swaps-840",
    "seed-placement-clustered",
    "seed-placement-dispersed",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_content_hash(value: Mapping[str, Any], expected: str) -> None:
    identity = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != expected or canonical_hash(identity) != expected:
        raise ValueError(f"Canonical content hash differs from {expected}")


def copy_canonical_artifacts() -> None:
    (RESULTS / "completion-manifests").mkdir(parents=True, exist_ok=True)
    (RESULTS / "checkpoints").mkdir(parents=True, exist_ok=True)
    (RESULTS / "invocation-journals").mkdir(parents=True, exist_ok=True)
    copies = {
        ROOT / "execution/gate1_2/pre-execution-receipt.json": (
            RESULTS / "pre-execution-receipt.json"
        ),
        ROOT / "execution/gate1_2/execution-authorization.json": (
            RESULTS / "execution-authorization.json"
        ),
        ROOT / "manifests/gate1_2_suite_v1.json": (
            RESULTS / "campaign-specification.json"
        ),
        RAW / "gate1_2-confirmatory-analysis.json": (
            RESULTS / "gate1_2-confirmatory-analysis.json"
        ),
        RAW / "suite-completion-manifest.json": (
            RESULTS / "suite-completion-manifest.json"
        ),
        RAW / "exact-replication/completion-manifest.json": (
            RESULTS / "completion-manifests/exact-replication.json"
        ),
        RAW / "exact-replication/checkpoint.json": (
            RESULTS / "checkpoints/exact-replication.json"
        ),
        RAW / "alternate-topology/completion-manifest.json": (
            RESULTS / "completion-manifests/alternate-topology.json"
        ),
        RAW / "alternate-topology/checkpoint.json": (
            RESULTS / "checkpoints/alternate-topology.json"
        ),
    }
    for cell_id in CELL_IDS:
        copies[
            RAW / f"standard-robustness/{cell_id}/completion-manifest.json"
        ] = RESULTS / f"completion-manifests/{cell_id}.json"
        copies[RAW / f"standard-robustness/{cell_id}/checkpoint.json"] = (
            RESULTS / f"checkpoints/{cell_id}.json"
        )
    for source, target in copies.items():
        shutil.copyfile(source, target)

    journal_sources = list((RAW / "exact-replication/journals").glob("*.json"))
    journal_sources += list((RAW / "alternate-topology/journals").glob("*.json"))
    for cell_id in CELL_IDS:
        journal_sources += list(
            (RAW / f"standard-robustness/{cell_id}/journals").glob("*.json")
        )
    for source in sorted(journal_sources):
        shutil.copyfile(source, RESULTS / "invocation-journals" / source.name)


def exact_condition_aggregates() -> dict[str, Any]:
    ring_count = 0
    rewired_count = 0
    denominator = 0
    paths = sorted((RAW / "exact-replication/chunks").glob("*.json"))
    if len(paths) != 3000:
        raise ValueError("Exact-replication raw chunk count differs")
    for path in paths:
        chunk = _read_json(path)
        if chunk.get("validity_status") != "VALID":
            raise ValueError("Exact-replication chunk is not valid")
        result = chunk["unit_result"]
        ring = result["conditions"]["ring"]["metrics"]["primary_endpoint"]
        rewired = result["conditions"]["rewired"]["metrics"]["primary_endpoint"]
        if ring["denominator"] != 54 or rewired["denominator"] != 54:
            raise ValueError("Exact-replication denominator differs")
        ring_count += int(ring["adopted_unseeded_count"])
        rewired_count += int(rewired["adopted_unseeded_count"])
        denominator += 54
    return {
        "ring": {
            "adoption_count": ring_count,
            "denominator": denominator,
            "mean_incidence": ring_count / denominator,
        },
        "rewired": {
            "adoption_count": rewired_count,
            "denominator": denominator,
            "mean_incidence": rewired_count / denominator,
        },
        "rewired_minus_ring_from_aggregates": (
            (rewired_count - ring_count) / denominator
        ),
    }


def invocation_accounting() -> dict[str, Any]:
    journals = [_read_json(path) for path in sorted((RESULTS / "invocation-journals").glob("*.json"))]
    if len(journals) != 13:
        raise ValueError("Invocation-journal count differs")
    list_fields = (
        "preexisting_valid",
        "newly_computed",
        "resumed",
        "interrupted",
        "skipped",
        "failed",
        "recomputed",
        "in_progress",
    )
    totals = {field: sum(len(journal[field]) for journal in journals) for field in list_fields}
    if totals != {
        "preexisting_valid": 813,
        "newly_computed": 14000,
        "resumed": 813,
        "interrupted": 0,
        "skipped": 0,
        "failed": 0,
        "recomputed": 0,
        "in_progress": 0,
    }:
        raise ValueError("Invocation accounting differs")
    return {
        "invocation_count": len(journals),
        "operator_process_interruptions": 1,
        "interrupted_temporary_files": 0,
        "newly_computed_unique_units": totals["newly_computed"],
        "preexisting_valid_observations": totals["preexisting_valid"],
        "resumed_valid_observations": totals["resumed"],
        "failed_units": totals["failed"],
        "skipped_units": totals["skipped"],
        "recomputed_units": totals["recomputed"],
        "unfinished_units": totals["in_progress"],
        "disclosure": (
            "The initial exact-replication process was stopped after 813 valid chunks "
            "to replace CPU-bound thread concurrency with process-level concurrency. "
            "The same frozen identities resumed all 813 valid chunks; no credited unit "
            "was recomputed and no temporary file remained."
        ),
    }


def build_derived_artifacts() -> None:
    copy_canonical_artifacts()
    suite = _read_json(RESULTS / "suite-completion-manifest.json")
    analysis = _read_json(RESULTS / "gate1_2-confirmatory-analysis.json")
    _verify_content_hash(suite, EXPECTED_SUITE_HASH)
    _verify_content_hash(analysis, EXPECTED_ANALYSIS_HASH)
    aggregates = exact_condition_aggregates()
    if aggregates["rewired_minus_ring_from_aggregates"] != analysis[
        "exact_replication"
    ]["paired_difference"]["estimate"]:
        raise ValueError("Exact-replication aggregate contrast differs from paired analysis")
    accounting = invocation_accounting()

    execution = {
        "schema_version": "gate12-execution-accounting-v1",
        "suite_id": "gate12-suite-v1",
        "suite_spec_hash": analysis["suite_spec_hash"],
        "implementation_commit": analysis["implementation_commit"],
        "implementation_source_hash": analysis["implementation_source_hash"],
        "completed_independent_units": suite["independent_unit_count"],
        "condition_runs": suite["condition_run_count"],
        "subcampaign_count": suite["subcampaign_count"],
        "invalid_units": suite["invalid_unit_count"],
        "missing_units": suite["missing_unit_count"],
        "duplicate_units": suite["duplicate_unit_count"],
        "analysis_run_count": 1,
        "invocations": accounting,
        "subcampaigns": suite["ordered_subcampaigns"],
        "suite_completion_hash": suite["content_hash"],
        "ordered_suite_ensemble_hash": suite["ordered_suite_ensemble_hash"],
    }
    _write_json(RESULTS / "execution-accounting.json", execution)

    passport = {
        "schema_version": "gate12-passport-v1",
        "status": "VALID_COMPLETE_UNPUBLISHED_CANDIDATE",
        "scientific_scope": (
            "Preregistered replication and robustness of a scripted independent-cascade "
            "topology benchmark; not evidence about LLM or real-agent social behavior."
        ),
        "authorities": {
            "gate1_1_result": {
                "commit": "43081df22f7b84ba16c2cf7e8edca28b45105ac4",
                "tag": "gate1.1-result-v1",
                "estimate": 0.048462962962962965,
            },
            "gate1_2_preregistration": {
                "commit": "c6e9506525d8e6088a6ecb6f417e375e040fd9aa",
                "tag": "gate1.2-prereg-v1",
                "document_sha256": (
                    "28e2240b159cad032dbf3d80f28a6d309f80fa11e5ebd9c3edd7d3bc230c8a17"
                ),
            },
            "gate1_2_implementation": {
                "certification_commit": "b4ca7b598215d14102969045e4717cd5007f1bc3",
                "tag": "gate1.2-impl-v1",
                "tag_object": "34fd68e4a40971164e2ba76d4fa8c5e0316c8edd",
                "scientific_code_commit": analysis["implementation_commit"],
                "source_bundle_sha256": analysis["implementation_source_hash"],
            },
            "campaign_specification": {
                "file_sha256": (
                    "89ff2c154a2fb093484c1e6a358de725455ff727ad65f5f88153081b6c60901d"
                ),
                "canonical_hash": analysis["suite_spec_hash"],
            },
        },
        "execution": execution,
        "primary_endpoint": (
            "final adoption incidence among initially unseeded agents at the frozen horizon"
        ),
        "exact_replication": {
            **aggregates,
            **analysis["exact_replication"],
        },
        "gate1_1_magnitude_comparison": analysis["cross_gate_magnitude"],
        "robustness_family": analysis["robustness_family"],
        "joint_classification": analysis["joint_classification"],
        "scientific_conclusion": (
            "The fresh-seed exact replication supported the directional topology effect "
            "and was magnitude-consistent with Gate 1.1. The frozen joint classification "
            "is replicated but specification-sensitive because not all eleven robustness "
            "point estimates were positive; there was no strong directional reversal."
        ),
        "limitations": [
            "This is a scripted independent-cascade benchmark, not LLM behavior.",
            "The result does not establish persuasion, autonomous norm formation, emergent intelligence, or general real-agent social behavior.",
            "The result is not presented as a novel network-science discovery.",
            "The practical five-percentage-point threshold and Hoeffding positivity certification were not met in exact replication.",
            "Strong family-wide robustness was not certified, and the dispersed-seed point estimate was negative but imprecise.",
        ],
        "integrity": {
            "suite_completion_hash": suite["content_hash"],
            "ordered_suite_ensemble_hash": suite["ordered_suite_ensemble_hash"],
            "confirmatory_analysis_content_hash": analysis["content_hash"],
            "confirmatory_analysis_file_sha256": _sha256(
                RESULTS / "gate1_2-confirmatory-analysis.json"
            ),
            "analysis_run_count": 1,
            "raw_chunks_in_compact_package": 0,
            "raw_chunks_cryptographically_represented": 14000,
        },
        "runtime_metadata": {
            "package_built_at_utc": BUILT_AT_UTC,
            "execution_language": "Python",
            "initial_exact_worker_count": 8,
            "resumed_exact_worker_count": 1,
            "parallel_subcampaign_processes": 12,
        },
    }
    _write_json(RESULTS / "gate1_2_passport.json", passport)

    reproduction = {
        "schema_version": "gate12-reproducibility-evidence-v1",
        "status": "PASS",
        "suite_id": suite["suite_id"],
        "suite_spec_hash": suite["suite_spec_hash"],
        "source_bundle_sha256": analysis["implementation_source_hash"],
        "checks": {
            "all_14000_chunk_hashes_validated": True,
            "all_30000_condition_results_schema_and_replay_validated": True,
            "twelve_child_manifests_reconstructed_from_chunks": True,
            "suite_manifest_reconstructed_from_child_manifests": True,
            "checkpoint_chunk_correspondence_validated": True,
            "alternate_topology_uses_1000_cluster_units": True,
            "no_nested_realization_pseudoreplication": True,
            "analysis_lock_opened_only_after_suite_verification": True,
            "analysis_run_count": 1,
            "serial_parallel_worker_invariance_certified_by_tests": True,
            "full_independent_second_production_computation_performed": False,
        },
        "non_recomputation_note": (
            "The 4.4 GB production chunk set was not recomputed as a second campaign. "
            "Certified replay, hash validation, checkpoint reconstruction, child-manifest "
            "reconstruction, and suite reconstruction were performed against every chunk."
        ),
        "canonical_hashes": {
            "suite_completion": suite["content_hash"],
            "ordered_suite_ensemble": suite["ordered_suite_ensemble_hash"],
            "confirmatory_analysis": analysis["content_hash"],
            "child_completion_manifests": {
                item["subcampaign_id"]: item["completion_manifest_hash"]
                for item in suite["ordered_subcampaigns"]
            },
            "child_ordered_ensembles": {
                item["subcampaign_id"]: item["ordered_ensemble_hash"]
                for item in suite["ordered_subcampaigns"]
            },
        },
        "reproduction_commands": [
            "python3 -m unittest discover -s tests -q",
            "python3 scripts/validate_gate12_implementation.py",
            "python3 scripts/validate_gate12_result.py",
            "python3 -m pasko_agent_society.gate12.cli --repository-root . verify-suite",
        ],
    }
    _write_json(RESULTS / "reproducibility-evidence.json", reproduction)


def write_evidence_index() -> None:
    excluded = {"evidence-index.json"}
    members = []
    for path in sorted(RESULTS.rglob("*")):
        if path.is_file() and path.name not in excluded:
            members.append(
                {
                    "file": path.relative_to(RESULTS).as_posix(),
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
    index = {
        "schema_version": "gate12-evidence-index-v1",
        "suite_id": "gate12-suite-v1",
        "package_status": "UNPUBLISHED_CANDIDATE",
        "package_members": members,
        "member_count": len(members),
        "total_member_bytes": sum(item["bytes"] for item in members),
        "raw_chunks_included": 0,
        "raw_chunks_represented_by_manifests": 14000,
        "suite_completion_content_hash": EXPECTED_SUITE_HASH,
        "analysis_content_hash": EXPECTED_ANALYSIS_HASH,
    }
    _write_json(RESULTS / "evidence-index.json", index)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-only", action="store_true")
    args = parser.parse_args()
    if args.index_only:
        write_evidence_index()
    else:
        build_derived_artifacts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
