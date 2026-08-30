#!/usr/bin/env python3
"""Validate the compact, unpublished Gate 1.2 result package."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "gate1_2"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.canonical import canonical_hash  # noqa: E402
from pasko_agent_society.gate12.analysis import validate_confirmatory_analysis  # noqa: E402
from pasko_agent_society.gate12.manifest import (  # noqa: E402
    implementation_source_hash,
    load_suite_spec,
)
from pasko_agent_society.gate12.storage import (  # noqa: E402
    production_contexts,
    validate_execution_authorization,
)


EXPECTED_EVIDENCE_INDEX_SHA256 = (
    "353d98b3fc1852fce42e7155d0da6ce2344e265c49ca04c4b26653ee0d472d2b"
)
EXPECTED_SUITE_FILE_SHA256 = (
    "2e7a5fd78fed7b5715516737f53c54a70f1e62c82659522b5cba4b187f36c7b3"
)
EXPECTED_SUITE_CONTENT_HASH = (
    "sha256:c111cd3bad274cd83b54298545112d513e5c216d391204b0b6bd56f68ebd332f"
)
EXPECTED_ORDERED_SUITE_HASH = (
    "sha256:7a2554574aa0083bc1007c6dd4c61d07aff86f38062d0ff83e0ee9985c604661"
)
EXPECTED_ANALYSIS_FILE_SHA256 = (
    "5095dfb4a6b3e692b94046a1128ed30c28da3de0b4eba8e7dd7e2a644d4f7c32"
)
EXPECTED_ANALYSIS_CONTENT_HASH = (
    "sha256:f1ab741de5b57e9ccaaab437299992538baa549d1bb2de4c59a5cd7c1220e7f0"
)
EXPECTED_SOURCE_SHA256 = (
    "bbbcffc40390a357337b154e9d6ed578e41f451fc8c6105a0ea3c83418311bf2"
)
EXPECTED_SPEC_FILE_SHA256 = (
    "89ff2c154a2fb093484c1e6a358de725455ff727ad65f5f88153081b6c60901d"
)
EXPECTED_SPEC_HASH = (
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
    "gate1.2-impl-v1": (
        "34fd68e4a40971164e2ba76d4fa8c5e0316c8edd",
        "b4ca7b598215d14102969045e4717cd5007f1bc3",
    ),
}
EXPECTED_GATE11_HASHES = {
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
EXPECTED_ESTIMATES = {
    "p-1-of-8": 0.005259259259259259,
    "p-3-of-8": 0.15322222222222223,
    "seeds-3": 0.03821052631578947,
    "seeds-12": 0.04672916666666666,
    "rounds-4": 0.02659259259259259,
    "rounds-12": 0.04366666666666667,
    "swaps-360": 0.050944444444444445,
    "swaps-840": 0.04607407407407407,
    "seed-placement-clustered": 0.19424074074074074,
    "seed-placement-dispersed": -0.003907407407407406,
    "alternate-topology-3": 0.04044444444444444,
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_text(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def _verify_content_hash(value: Mapping[str, Any], expected: str | None = None) -> None:
    identity = {key: item for key, item in value.items() if key != "content_hash"}
    computed = canonical_hash(identity)
    if value.get("content_hash") != computed:
        raise ValueError("Canonical content hash differs")
    if expected is not None and computed != expected:
        raise ValueError(f"Canonical content hash differs from {expected}")


def _completion_filename(item: Mapping[str, Any]) -> str:
    if item["subcampaign_id"] == "gate12-replication-3000-v1":
        return "exact-replication.json"
    if item["subcampaign_id"] == "gate12-alt-topology-1000-v1":
        return "alternate-topology.json"
    return f"{item['cell_id']}.json"


def _validate_index() -> dict[str, Any]:
    path = RESULTS / "evidence-index.json"
    if EXPECTED_EVIDENCE_INDEX_SHA256 != "PENDING" and _sha256(path) != (
        EXPECTED_EVIDENCE_INDEX_SHA256
    ):
        raise ValueError("Evidence-index file hash differs")
    index = _read_json(path)
    if index.get("schema_version") != "gate12-evidence-index-v1":
        raise ValueError("Evidence-index schema differs")
    members = index.get("package_members")
    if not isinstance(members, list) or index.get("member_count") != len(members):
        raise ValueError("Evidence-index member count differs")
    indexed_names: set[str] = set()
    total_bytes = 0
    for member in members:
        if not isinstance(member, dict) or set(member) != {"file", "sha256", "bytes"}:
            raise ValueError("Evidence-index member schema differs")
        relative = Path(str(member["file"]))
        if relative.is_absolute() or ".." in relative.parts or "chunks" in relative.parts:
            raise ValueError("Evidence-index path is unsafe or includes raw chunks")
        member_path = RESULTS / relative
        if not member_path.is_file():
            raise ValueError(f"Indexed member is absent: {relative}")
        if _sha256(member_path) != member["sha256"] or member_path.stat().st_size != member[
            "bytes"
        ]:
            raise ValueError(f"Evidence-index member differs: {relative}")
        indexed_names.add(relative.as_posix())
        total_bytes += member_path.stat().st_size
    actual_names = {
        path.relative_to(RESULTS).as_posix()
        for path in RESULTS.rglob("*")
        if path.is_file() and path.name != "evidence-index.json"
    }
    if indexed_names != actual_names or index.get("total_member_bytes") != total_bytes:
        raise ValueError("Evidence-index membership or byte count differs")
    if index.get("raw_chunks_included") != 0 or index.get(
        "raw_chunks_represented_by_manifests"
    ) != 14000:
        raise ValueError("Evidence-index raw-chunk boundary differs")
    return index


def validate_result_package() -> dict[str, Any]:
    index = _validate_index()
    manifest_path = RESULTS / "campaign-specification.json"
    if _sha256(manifest_path) != EXPECTED_SPEC_FILE_SHA256:
        raise ValueError("Campaign-specification file hash differs")
    if manifest_path.read_bytes() != (ROOT / "manifests/gate1_2_suite_v1.json").read_bytes():
        raise ValueError("Packaged and repository campaign specifications differ")
    spec = load_suite_spec(manifest_path, require_certified=True)
    if spec.spec_hash != EXPECTED_SPEC_HASH or implementation_source_hash(ROOT) != (
        EXPECTED_SOURCE_SHA256
    ):
        raise ValueError("Campaign or source identity differs")

    authorization = _read_json(RESULTS / "execution-authorization.json")
    validate_execution_authorization(production_contexts(spec), authorization)
    receipt = _read_json(RESULTS / "pre-execution-receipt.json")
    if receipt.get("status", {}).get("production_outcome_generating_runs") != 0:
        raise ValueError("Pre-execution zero-data receipt differs")
    if receipt.get("status", {}).get("independent_units_pending") != 14000:
        raise ValueError("Pre-execution pending count differs")

    suite_path = RESULTS / "suite-completion-manifest.json"
    if _sha256(suite_path) != EXPECTED_SUITE_FILE_SHA256:
        raise ValueError("Suite-completion file hash differs")
    suite = _read_json(suite_path)
    _verify_content_hash(suite, EXPECTED_SUITE_CONTENT_HASH)
    if {
        "units": suite.get("independent_unit_count"),
        "runs": suite.get("condition_run_count"),
        "subcampaigns": suite.get("subcampaign_count"),
        "invalid": suite.get("invalid_unit_count"),
        "missing": suite.get("missing_unit_count"),
        "duplicates": suite.get("duplicate_unit_count"),
        "ensemble": suite.get("ordered_suite_ensemble_hash"),
    } != {
        "units": 14000,
        "runs": 30000,
        "subcampaigns": 12,
        "invalid": 0,
        "missing": 0,
        "duplicates": 0,
        "ensemble": EXPECTED_ORDERED_SUITE_HASH,
    }:
        raise ValueError("Suite-completion counts or ensemble differ")

    unit_total = 0
    for item in suite["ordered_subcampaigns"]:
        filename = _completion_filename(item)
        completion = _read_json(RESULTS / "completion-manifests" / filename)
        checkpoint = _read_json(RESULTS / "checkpoints" / filename)
        _verify_content_hash(completion, str(item["completion_manifest_hash"]))
        _verify_content_hash(checkpoint)
        if completion.get("ordered_ensemble_hash") != item["ordered_ensemble_hash"]:
            raise ValueError(f"Child ensemble differs: {filename}")
        ordered = completion.get("ordered_chunks")
        if not isinstance(ordered, list) or len(ordered) != item["valid_unit_count"]:
            raise ValueError(f"Child ordered units differ: {filename}")
        expected_hashes = {entry["unit_id"]: entry["chunk_hash"] for entry in ordered}
        if checkpoint.get("valid_chunk_hashes") != expected_hashes:
            raise ValueError(f"Checkpoint and completion differ: {filename}")
        if checkpoint.get("counts") != {
            "completed": item["valid_unit_count"],
            "interrupted_temporary_files": 0,
            "invalid": 0,
            "pending": 0,
        }:
            raise ValueError(f"Checkpoint counts differ: {filename}")
        unit_total += int(item["valid_unit_count"])
    if unit_total != 14000:
        raise ValueError("Child-manifest unit total differs")

    analysis_path = RESULTS / "gate1_2-confirmatory-analysis.json"
    if _sha256(analysis_path) != EXPECTED_ANALYSIS_FILE_SHA256:
        raise ValueError("Confirmatory-analysis file hash differs")
    analysis = _read_json(analysis_path)
    _verify_content_hash(analysis, EXPECTED_ANALYSIS_CONTENT_HASH)
    validate_confirmatory_analysis(
        analysis,
        suite_id="gate12-suite-v1",
        suite_spec_hash=EXPECTED_SPEC_HASH,
        implementation_commit="798985dc77dac6a327848ff4c29445417a616094",
        implementation_source_hash=EXPECTED_SOURCE_SHA256,
        suite_completion_hash=EXPECTED_SUITE_CONTENT_HASH,
    )
    exact = analysis["exact_replication"]
    paired = exact["paired_difference"]
    if {
        "estimate": paired["estimate"],
        "lower": paired["lower"],
        "upper": paired["upper"],
        "support": exact["directional_support"],
        "practical": exact["practical_magnitude"]["threshold_met"],
        "hoeffding": exact["hoeffding"]["certified_positive"],
    } != {
        "estimate": 0.04810493827160494,
        "lower": 0.04272786632773895,
        "upper": 0.05348201021547093,
        "support": True,
        "practical": False,
        "hoeffding": False,
    }:
        raise ValueError("Exact-replication result differs")
    cells = analysis["robustness_family"]["cells"]
    if {cell["cell_id"]: cell["estimate"] for cell in cells} != EXPECTED_ESTIMATES:
        raise ValueError("Robustness estimates differ")
    if analysis["robustness_family"]["all_point_estimates_positive"] is not False:
        raise ValueError("Robustness sign flag differs")
    if analysis["robustness_family"]["strong_robustness_certified"] is not False:
        raise ValueError("Strong-robustness flag differs")
    if analysis["robustness_family"]["strong_directional_reversal"] is not False:
        raise ValueError("Strong-reversal flag differs")
    if analysis["joint_classification"]["classification"] != (
        "replicated but specification-sensitive"
    ):
        raise ValueError("Joint classification differs")
    if analysis["cross_gate_magnitude"]["classification"] != (
        "consistent within five percentage points"
    ):
        raise ValueError("Cross-gate magnitude classification differs")

    passport = _read_json(RESULTS / "gate1_2_passport.json")
    if passport.get("status") != "VALID_COMPLETE_UNPUBLISHED_CANDIDATE":
        raise ValueError("Passport status differs")
    if passport["exact_replication"]["ring"] != {
        "adoption_count": 31996,
        "denominator": 162000,
        "mean_incidence": 0.19750617283950617,
    }:
        raise ValueError("Passport ring aggregate differs")
    if passport["exact_replication"]["rewired"] != {
        "adoption_count": 39789,
        "denominator": 162000,
        "mean_incidence": 0.2456111111111111,
    }:
        raise ValueError("Passport rewired aggregate differs")
    if passport["joint_classification"] != analysis["joint_classification"]:
        raise ValueError("Passport classification differs from analysis")

    accounting = _read_json(RESULTS / "execution-accounting.json")
    if {
        "completed": accounting.get("completed_independent_units"),
        "runs": accounting.get("condition_runs"),
        "analysis_runs": accounting.get("analysis_run_count"),
        "invalid": accounting.get("invalid_units"),
        "missing": accounting.get("missing_units"),
        "duplicate": accounting.get("duplicate_units"),
        "resumed": accounting.get("invocations", {}).get("resumed_valid_observations"),
        "recomputed": accounting.get("invocations", {}).get("recomputed_units"),
    } != {
        "completed": 14000,
        "runs": 30000,
        "analysis_runs": 1,
        "invalid": 0,
        "missing": 0,
        "duplicate": 0,
        "resumed": 813,
        "recomputed": 0,
    }:
        raise ValueError("Execution accounting differs")
    journals = list((RESULTS / "invocation-journals").glob("*.json"))
    if len(journals) != 13:
        raise ValueError("Invocation-journal count differs")

    reproduction = _read_json(RESULTS / "reproducibility-evidence.json")
    validation = _read_json(RESULTS / "validation-report.json")
    if reproduction.get("status") != "PASS" or validation.get("status") != "PASS":
        raise ValueError("Reproducibility or validation report does not pass")
    if validation.get("package_boundary", {}).get("gate2_started") is not False:
        raise ValueError("Gate 2 boundary differs")

    for tag, (expected_object, expected_target) in EXPECTED_TAGS.items():
        if _git_text("rev-parse", tag) != expected_object:
            raise ValueError(f"Annotated tag object differs for {tag}")
        if _git_text("rev-parse", f"{tag}^{{}}") != expected_target:
            raise ValueError(f"Annotated tag target differs for {tag}")
    for name, expected in EXPECTED_GATE11_HASHES.items():
        if _sha256(ROOT / "results" / "gate1_1" / name) != expected:
            raise ValueError(f"Gate 1.1 public result hash differs: {name}")

    if _git_text("ls-files", "artifacts/gate1_2_v1/**"):
        raise ValueError("Raw Gate 1.2 artifacts are tracked")
    if _git_text("ls-files", "results/gate1_2/**/chunks/**"):
        raise ValueError("Raw Gate 1.2 chunks entered the compact package")
    if (ROOT / "pasko_agent_society" / "gate12" / "llm_adapter.py").exists():
        raise ValueError("An LLM adapter entered Gate 1.2")
    if any((ROOT / "pasko_agent_society").glob("gate2*")):
        raise ValueError("Gate 2 implementation entered the repository")

    return {
        "schema_version": "gate12-result-package-validation-v1",
        "status": "PASS",
        "suite_id": "gate12-suite-v1",
        "independent_units": 14000,
        "condition_runs": 30000,
        "invalid_units": 0,
        "analysis_run_count": 1,
        "suite_completion_hash": EXPECTED_SUITE_CONTENT_HASH,
        "ordered_suite_ensemble_hash": EXPECTED_ORDERED_SUITE_HASH,
        "analysis_content_hash": EXPECTED_ANALYSIS_CONTENT_HASH,
        "joint_classification": "replicated but specification-sensitive",
        "evidence_index_sha256": _sha256(RESULTS / "evidence-index.json"),
        "package_member_count": index["member_count"],
        "raw_chunks_tracked": 0,
        "gate2_started": False,
    }


def main() -> int:
    print(json.dumps(validate_result_package(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
