#!/usr/bin/env python3
"""Validate the frozen, compact Gate 1.1 public result package."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "gate1_1"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.canonical import canonical_hash  # noqa: E402
from pasko_agent_society.gate11_manifest import (  # noqa: E402
    implementation_source_hash,
)

EXPECTED_FILE_SHA256 = {
    "GATE_1_1_RESULT_REPORT.md": "7df93c11bcb2e5015112951122cb6e06526d6d976d76bcf04fbd99cbbe00e419",
    "evidence-index.json": "648826dadfd52bb6fe572ee3532a23f6266074113768fa7e279f636167d147ba",
    "gate1_1_passport.json": "a61ca9010b732f315b34ac89b57bfd1b340093814bd6161b668e77f4943bc2d7",
    "primary-analysis.json": "7e0731418f74accedd787895dd99e5b0b2243388c5470b18ec45ed361e390248",
}
EXPECTED_CONTENT_HASHES = {
    "checkpoint": "sha256:9738b04bac0b3fa89af95e4f8d6e4515b611772d390cc8d6183626ee40cc5b9e",
    "completion": "sha256:161e575ca0e56867d4f98ae4159a4214055e93d20062209dcd40639a8502dd86",
    "ensemble": "sha256:f511edb2eb742f8220d94580757320d53546bc9f323cabd0ba0131fb20b64fbd",
    "analysis": "sha256:a910f13451e642ca57e81a8b2e1bfa04b9705aabbabe5d63cfde0e7e220a4ca8",
}
EXPECTED_TAGS = {
    "gate1.1-prereg-v1": (
        "ea551b44ca83f44ffa134d92cd2694dc1b53424c",
        "cc1ab868a7401099751030580649e49258654fe2",
    ),
    "gate1.1-impl-v1": (
        "0d065d9f0486b08bfbc9db42fefaf52a962c948b",
        "4c8bb4d3f88a38469a6edcb770b1b0a037a73ae7",
    ),
    "gate1.2-prereg-v1": (
        "08d0a5db354d166d5313a815dc87a8917fd1ecd4",
        "c6e9506525d8e6088a6ecb6f417e375e040fd9aa",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(name: str) -> dict[str, Any]:
    value = json.loads((RESULTS / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{name} is not a JSON object")
    return value


def _git_text(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def _git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.STDOUT)


def _verify_content_hash(value: dict[str, Any], expected: str) -> None:
    identity = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != expected or canonical_hash(identity) != expected:
        raise ValueError(f"Canonical content hash differs from {expected}")


def validate_result_package() -> dict[str, Any]:
    expected_names = {
        "GATE_1_1_RESULT_REPORT.md",
        "checkpoint.json",
        "completion-manifest.json",
        "evidence-index.json",
        "execution-authorization.json",
        "gate1_1_passport.json",
        "pre-execution-receipt.json",
        "primary-analysis.json",
        "reproducibility-evidence.json",
        "validation-report.json",
    }
    actual_names = {path.name for path in RESULTS.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise ValueError("Compact result package has missing or unknown files")

    for name, expected in EXPECTED_FILE_SHA256.items():
        if _sha256(RESULTS / name) != expected:
            raise ValueError(f"Reviewed file hash differs for {name}")

    evidence = _read_json("evidence-index.json")
    if evidence.get("schema_version") != "gate11-evidence-index-v1":
        raise ValueError("Evidence-index schema differs")
    members = evidence.get("package_members")
    if not isinstance(members, list) or len(members) != 9:
        raise ValueError("Evidence-index member list differs")
    indexed_names: set[str] = set()
    for member in members:
        if not isinstance(member, dict) or set(member) != {"file", "sha256"}:
            raise ValueError("Evidence-index member schema differs")
        name = str(member["file"])
        indexed_names.add(name)
        if _sha256(RESULTS / name) != member["sha256"]:
            raise ValueError(f"Evidence member hash differs for {name}")
    if indexed_names != expected_names - {"evidence-index.json"}:
        raise ValueError("Evidence-index membership differs")

    checkpoint = _read_json("checkpoint.json")
    completion = _read_json("completion-manifest.json")
    analysis = _read_json("primary-analysis.json")
    passport = _read_json("gate1_1_passport.json")
    receipt = _read_json("pre-execution-receipt.json")
    authorization = _read_json("execution-authorization.json")
    reproduction = _read_json("reproducibility-evidence.json")
    validation = _read_json("validation-report.json")

    _verify_content_hash(checkpoint, EXPECTED_CONTENT_HASHES["checkpoint"])
    _verify_content_hash(completion, EXPECTED_CONTENT_HASHES["completion"])
    _verify_content_hash(analysis, EXPECTED_CONTENT_HASHES["analysis"])

    ordered = completion.get("ordered_chunks")
    if not isinstance(ordered, list) or len(ordered) != 3000:
        raise ValueError("Completion manifest does not contain 3,000 ordered chunks")
    pair_ids = [str(item["pair_id"]) for item in ordered]
    if len(set(pair_ids)) != 3000:
        raise ValueError("Completion manifest pair identities are not unique")
    if completion.get("ordered_ensemble_hash") != EXPECTED_CONTENT_HASHES["ensemble"]:
        raise ValueError("Ordered ensemble hash differs")
    if {
        "valid_pair_count": completion.get("valid_pair_count"),
        "invalid_pair_count": completion.get("invalid_pair_count"),
        "missing_pair_count": completion.get("missing_pair_count"),
        "duplicate_pair_count": completion.get("duplicate_pair_count"),
    } != {
        "valid_pair_count": 3000,
        "invalid_pair_count": 0,
        "missing_pair_count": 0,
        "duplicate_pair_count": 0,
    }:
        raise ValueError("Completion counts differ")
    expected_chunk_hashes = {
        str(item["pair_id"]): str(item["chunk_hash"]) for item in ordered
    }
    if checkpoint.get("valid_chunk_hashes") != expected_chunk_hashes:
        raise ValueError("Checkpoint and completion manifest differ")
    if checkpoint.get("counts") != {
        "completed": 3000,
        "interrupted_temporary_files": 0,
        "invalid": 0,
        "pending": 0,
    }:
        raise ValueError("Checkpoint counts differ")

    statistics = analysis.get("statistics", {})
    if analysis.get("decision") != "SUPPORT_H1":
        raise ValueError("Primary decision differs")
    if statistics.get("ring") != {
        "adoption_count": 31569,
        "denominator": 162000,
        "mean_incidence": 0.19487037037037036,
    }:
        raise ValueError("Ring aggregate differs")
    if statistics.get("rewired") != {
        "adoption_count": 39420,
        "denominator": 162000,
        "mean_incidence": 0.24333333333333335,
    }:
        raise ValueError("Rewired aggregate differs")
    if statistics.get("paired_difference", {}).get("estimate") != 0.048462962962962965:
        raise ValueError("Primary estimate differs")
    if statistics.get("primary_interval", {}).get("lower") != 0.04307658465756581:
        raise ValueError("Primary lower confidence bound differs")
    if statistics.get("primary_interval", {}).get("upper") != 0.05384934126836012:
        raise ValueError("Primary upper confidence bound differs")
    if statistics.get("practical_magnitude", {}).get("threshold_met") is not False:
        raise ValueError("Practical-magnitude classification differs")
    if (
        statistics.get("distribution_free_conservative_certification", {}).get(
            "certified_positive"
        )
        is not False
    ):
        raise ValueError("Hoeffding certification differs")

    if passport.get("analysis", {}).get("analysis_run_count") != 1:
        raise ValueError("Primary analysis run count differs")
    if passport.get("result", {}).get("h1_decision") != "SUPPORT_H1":
        raise ValueError("Passport primary decision differs")
    if receipt.get("status") != {
        "checkpoint_hash": None,
        "completed": 0,
        "integrity_status": "PASS",
        "invalid": 0,
        "pending": 3000,
        "primary_outcome_generating_runs": 0,
    }:
        raise ValueError("Zero-data receipt differs")
    if authorization != {
        "authorization_id": "gate11-primary-execution-v1",
        "authorized": True,
        "campaign_id": "gate11-primary-3000-v1",
        "campaign_spec_hash": "sha256:76ceaf1e182b5b6ecbe8214a694b4000d47d495165ab025f15112901e71600f2",
        "implementation_commit": "d31c78011abfc164fd3d20125bbe995e4023ee4a",
        "implementation_source_hash": "c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09",
        "pair_count": 3000,
        "schema_version": "gate11-execution-authorization-v1",
        "scope": "RUN_3000_MATCHED_PAIRS",
    }:
        raise ValueError("Execution authorization differs")
    if reproduction.get("status") != "PASS" or not reproduction.get(
        "comparisons", {}
    ).get("serial_parallel_equivalence"):
        raise ValueError("Reproduction evidence differs")
    if validation.get("campaign_integrity", {}).get("status") != "PASS":
        raise ValueError("Validation report does not pass")
    if validation.get("gate1_2", {}).get("execution_count") != 0:
        raise ValueError("Gate 1.2 execution is not zero")

    if _sha256(ROOT / "preregistrations" / "GATE_1_1_PREREGISTRATION.md") != (
        "e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706"
    ):
        raise ValueError("Gate 1.1 preregistration bytes differ")
    gate12_bytes = _git_bytes(
        "show",
        "gate1.2-prereg-v1:preregistrations/GATE_1_2_PREREGISTRATION.md",
    )
    if hashlib.sha256(gate12_bytes).hexdigest() != (
        "28e2240b159cad032dbf3d80f28a6d309f80fa11e5ebd9c3edd7d3bc230c8a17"
    ):
        raise ValueError("Gate 1.2 preregistration bytes differ")
    if implementation_source_hash() != (
        "c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09"
    ):
        raise ValueError("Scientific source-bundle hash differs")
    for tag, (expected_object, expected_target) in EXPECTED_TAGS.items():
        if _git_text("rev-parse", tag) != expected_object:
            raise ValueError(f"Annotated tag object differs for {tag}")
        if _git_text("rev-parse", f"{tag}^{{}}") != expected_target:
            raise ValueError(f"Annotated tag target differs for {tag}")

    tracked_primary = _git_text("ls-files", "*primary-analysis.json").splitlines()
    if tracked_primary != ["results/gate1_1/primary-analysis.json"]:
        raise ValueError("Primary analysis is missing or duplicated in tracked evidence")
    if _git_text("ls-files", "artifacts/gate1_1_primary_v1/**"):
        raise ValueError("Raw production artifacts are tracked")
    if _git_text("ls-files", "results/gate1_2/**", "artifacts/*gate1_2*"):
        raise ValueError("Gate 1.2 execution artifacts are tracked")

    return {
        "schema_version": "gate11-public-result-validation-v1",
        "status": "PASS",
        "campaign_id": "gate11-primary-3000-v1",
        "matched_pairs": 3000,
        "condition_runs": 6000,
        "primary_analysis_run_count": 1,
        "gate1_2_execution_count": 0,
        "evidence_index_sha256": EXPECTED_FILE_SHA256["evidence-index.json"],
        "primary_analysis_content_hash": EXPECTED_CONTENT_HASHES["analysis"],
        "ordered_ensemble_hash": EXPECTED_CONTENT_HASHES["ensemble"],
        "raw_chunks_tracked": 0,
    }


def main() -> int:
    print(json.dumps(validate_result_package(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
