#!/usr/bin/env python3
"""Validate the outcome-free Gate 1.2 certified implementation candidate."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from pasko_agent_society.gate12.manifest import (  # noqa: E402
    implementation_source_hash,
    load_suite_spec,
)
from pasko_agent_society.gate12.registry import (  # noqa: E402
    ALL_ROBUSTNESS_CONTRAST_IDS,
    GATE12_PREREGISTRATION_SHA256,
    ROBUSTNESS_CELL_IDS,
)
from validate_gate11_result import validate_result_package  # noqa: E402


MANIFEST = ROOT / "manifests" / "gate1_2_suite_v1.json"
PREREGISTRATION = ROOT / "preregistrations" / "GATE_1_2_PREREGISTRATION.md"

EXPECTED_MERGE_COMMIT = "8b172529300e416aad2d8e7c8512d9b62f6c66f3"
EXPECTED_MERGE_PARENTS = (
    "43081df22f7b84ba16c2cf7e8edca28b45105ac4",
    "c6e9506525d8e6088a6ecb6f417e375e040fd9aa",
)
EXPECTED_IMPLEMENTATION_COMMIT = "798985dc77dac6a327848ff4c29445417a616094"
EXPECTED_SOURCE_SHA256 = (
    "bbbcffc40390a357337b154e9d6ed578e41f451fc8c6105a0ea3c83418311bf2"
)
EXPECTED_MANIFEST_SHA256 = (
    "89ff2c154a2fb093484c1e6a358de725455ff727ad65f5f88153081b6c60901d"
)
EXPECTED_MANIFEST_CANONICAL_HASH = (
    "sha256:f529f43d05228602ec4d13684b928d7f390fdbb7962f3805ff408af8fa32ee54"
)
EXPECTED_TAGS = {
    "gate1.1-result-v1": (
        "cc2d41961c1790983da16a22171820de9af84e83",
        "43081df22f7b84ba16c2cf7e8edca28b45105ac4",
    ),
    "gate1.2-prereg-v1": (
        "08d0a5db354d166d5313a815dc87a8917fd1ecd4",
        "c6e9506525d8e6088a6ecb6f417e375e040fd9aa",
    ),
}
EXPECTED_GATE11_PUBLIC_HASHES = {
    "GATE_1_1_RESULT_REPORT.md": (
        "7df93c11bcb2e5015112951122cb6e06526d6d976d76bcf04fbd99cbbe00e419"
    ),
    "gate1_1_passport.json": (
        "a61ca9010b732f315b34ac89b57bfd1b340093814bd6161b668e77f4943bc2d7"
    ),
    "evidence-index.json": (
        "648826dadfd52bb6fe572ee3532a23f6266074113768fa7e279f636167d147ba"
    ),
    "primary-analysis.json": (
        "7e0731418f74accedd787895dd99e5b0b2243388c5470b18ec45ed361e390248"
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_text(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def _require_ancestor(commit: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Required provenance commit is not an ancestor: {commit}")


def _assert_no_gate12_outcomes() -> None:
    prohibited_paths = (
        ROOT / "artifacts" / "gate1_2_v1",
        ROOT / "results" / "gate1_2",
    )
    existing = [path.relative_to(ROOT).as_posix() for path in prohibited_paths if path.exists()]
    if existing:
        raise ValueError(f"Gate 1.2 production artifact path exists: {existing}")

    tracked = _git_text(
        "ls-files",
        "artifacts/gate1_2_v1/**",
        "results/gate1_2/**",
        "*gate1_2*authorization*.json",
    ).splitlines()
    if tracked:
        raise ValueError(f"Gate 1.2 production artifacts are tracked: {tracked}")

    forbidden_names = {
        "gate1_2-confirmatory-analysis.json",
        "suite-completion-manifest.json",
    }
    unexpected = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.relative_to(ROOT).parts
        and path.name in forbidden_names
    ]
    if unexpected:
        raise ValueError(f"Gate 1.2 completion or analysis artifact exists: {unexpected}")


def validate_implementation() -> dict[str, Any]:
    spec = load_suite_spec(MANIFEST, require_certified=True)
    if _sha256(MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Gate 1.2 suite-manifest file hash differs")
    if spec.spec_hash != EXPECTED_MANIFEST_CANONICAL_HASH:
        raise ValueError("Gate 1.2 suite-manifest canonical hash differs")
    if spec.implementation_commit != EXPECTED_IMPLEMENTATION_COMMIT:
        raise ValueError("Gate 1.2 scientific implementation commit differs")
    if spec.implementation_source_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError("Gate 1.2 bound source hash differs")
    if implementation_source_hash(ROOT) != EXPECTED_SOURCE_SHA256:
        raise ValueError("Gate 1.2 working source bundle differs")

    if _sha256(PREREGISTRATION) != GATE12_PREREGISTRATION_SHA256:
        raise ValueError("Frozen Gate 1.2 preregistration bytes differ")
    tag_bytes = subprocess.check_output(
        [
            "git",
            "show",
            "gate1.2-prereg-v1:preregistrations/GATE_1_2_PREREGISTRATION.md",
        ],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
    )
    if hashlib.sha256(tag_bytes).hexdigest() != GATE12_PREREGISTRATION_SHA256:
        raise ValueError("Tagged Gate 1.2 preregistration bytes differ")

    parents = tuple(_git_text("show", "-s", "--format=%P", EXPECTED_MERGE_COMMIT).split())
    if parents != EXPECTED_MERGE_PARENTS:
        raise ValueError("Gate 1.2 provenance merge parents differ")
    for commit in (*EXPECTED_MERGE_PARENTS, EXPECTED_MERGE_COMMIT, EXPECTED_IMPLEMENTATION_COMMIT):
        _require_ancestor(commit)
    package_diff = subprocess.run(
        ["git", "diff", "--quiet", EXPECTED_IMPLEMENTATION_COMMIT, "--", "pasko_agent_society"],
        cwd=ROOT,
        check=False,
    )
    if package_diff.returncode != 0:
        raise ValueError("Package source differs from the frozen scientific-code commit")

    for tag, (expected_object, expected_target) in EXPECTED_TAGS.items():
        if _git_text("rev-parse", tag) != expected_object:
            raise ValueError(f"Annotated tag object differs for {tag}")
        if _git_text("rev-parse", f"{tag}^{{}}") != expected_target:
            raise ValueError(f"Annotated tag target differs for {tag}")

    gate11 = validate_result_package()
    if gate11.get("status") != "PASS" or gate11.get("gate1_2_execution_count") != 0:
        raise ValueError("Gate 1.1 public result regression validation differs")
    for name, expected in EXPECTED_GATE11_PUBLIC_HASHES.items():
        if _sha256(ROOT / "results" / "gate1_1" / name) != expected:
            raise ValueError(f"Gate 1.1 public result hash differs for {name}")

    families = spec.raw["campaign_families"]
    if len(families["standard_robustness"]["cells"]) != 10:
        raise ValueError("Standard robustness cell count differs")
    if tuple(item["cell_id"] for item in families["standard_robustness"]["cells"]) != (
        ROBUSTNESS_CELL_IDS
    ):
        raise ValueError("Standard robustness cell order or identity differs")
    if tuple(spec.raw["analysis"]["robustness_family"]["contrast_ids"]) != (
        ALL_ROBUSTNESS_CONTRAST_IDS
    ):
        raise ValueError("Robustness contrast registry differs")
    if spec.raw["expected_artifacts"] != {
        "cluster_chunks": 1000,
        "condition_runs": 30000,
        "confirmatory_analyses": 1,
        "gate12_passports": 1,
        "independent_units": 14000,
        "pair_chunks": 13000,
        "scripted_agent_runs": 1800000,
        "subcampaign_completion_manifests": 12,
        "suite_completion_manifests": 1,
    }:
        raise ValueError("Frozen Gate 1.2 artifact counts differ")

    _assert_no_gate12_outcomes()
    return {
        "schema_version": "gate12-implementation-certification-validation-v1",
        "status": "PASS",
        "protocol_id": spec.raw["protocol"]["protocol_id"],
        "preregistration_sha256": GATE12_PREREGISTRATION_SHA256,
        "provenance_merge_commit": EXPECTED_MERGE_COMMIT,
        "scientific_implementation_commit": EXPECTED_IMPLEMENTATION_COMMIT,
        "source_bundle_sha256": EXPECTED_SOURCE_SHA256,
        "suite_manifest_file_sha256": EXPECTED_MANIFEST_SHA256,
        "suite_manifest_canonical_hash": EXPECTED_MANIFEST_CANONICAL_HASH,
        "independent_units_planned": 14000,
        "condition_runs_planned": 30000,
        "robustness_contrasts": 11,
        "gate1_1_regression": "PASS",
        "gate1_2_production_outcome_generating_runs": 0,
    }


def main() -> int:
    print(json.dumps(validate_implementation(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
