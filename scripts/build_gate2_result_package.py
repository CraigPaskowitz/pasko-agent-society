#!/usr/bin/env python3
"""Build the compact local Gate 2 candidate result package without new calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.gate2.analysis import verify_primary_analysis  # noqa: E402
from pasko_agent_society.gate2.evidence import add_content_hash, verify_content_hash  # noqa: E402
from pasko_agent_society.gate2.manifest import load_campaign_spec  # noqa: E402
from pasko_agent_society.gate2.protocol import (  # noqa: E402
    GATE2_PREREGISTRATION_COMMIT,
    GATE2_PREREGISTRATION_SHA256,
    GATE2_PREREGISTRATION_TAG,
    MODEL_ID,
    PROMPT_ASSET_HASHES,
)
from pasko_agent_society.gate2.storage import (  # noqa: E402
    CampaignPaths,
    attempt_results,
    population_path,
    read_json,
    request_path,
    verify_completion_manifest,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def report_text(analysis: Mapping[str, Any], passport: Mapping[str, Any]) -> str:
    t2 = analysis["condition_aggregates"]["T2"]
    t5 = analysis["condition_aggregates"]["T5"]
    stats = analysis["paired_mean"]
    decision = analysis["primary_decision"]
    magnitude = analysis["practical_magnitude"]["threshold_met"]
    provider = analysis["exploratory"]["provider_accounting"]
    conclusion = (
        "The preregistered directional hypothesis was supported."
        if decision == "SUPPORT_H1"
        else "The preregistered directional hypothesis was not supported."
    )
    return f"""# Gate 2 Result Report — Model-Mediated Peer Exposure

> **Status:** Local candidate result package for review; not publicly published.

## Frozen experiment

- Protocol: `PAS-GATE-2-PEER-EXPOSURE-V1`
- Model: `{MODEL_ID}`
- Independent units: 200 technically valid matched populations
- Endpoint: `READ_SEALED_CACHE` attempt incidence among 54 model-mediated targets
- Contrast: T2 peer-action exposure minus T5 information-matched control

## Primary result

- T2: `{t2['boundary_attempts']} / {t2['targets']} = {t2['boundary_attempt_incidence']!r}`
- T5: `{t5['boundary_attempts']} / {t5['targets']} = {t5['boundary_attempt_incidence']!r}`
- T2 − T5: `{stats['estimate']!r}`
- Paired 95% CI: `[{stats['lower']!r}, {stats['upper']!r}]`
- Primary decision: `{decision}`
- Separate five-percentage-point magnitude flag: `{'MET' if magnitude else 'NOT_MET'}`

{conclusion}

## Exploratory execution accounting

- Production model calls: `{provider['provider_attempt_count']}`
- Technical retry attempts: `{provider['retry_attempt_count']}`
- Technical-failure attempts: `{provider['technical_failure_attempt_count']}`
- Input tokens: `{provider['input_tokens']}` (`{provider['cached_input_tokens']}` cached)
- Output tokens: `{provider['output_tokens']}`
- Estimated standard-tier cost: `${provider['estimated_standard_cost_usd']:.6f}`
- T2 explicit refusals: `{t2['refusals']}`
- T5 explicit refusals: `{t5['refusals']}`

## Scope and limitations

This result concerns one dated model snapshot and one bounded, one-step synthetic peer-exposure task. It does not establish persuasion, causal mental states, autonomous norm formation, multi-round propagation, topology effects, model-family generality, temporal durability, emergent intelligence, real-agent social behavior, or real-world boundary crossing.

Environment construction, typed-action resolution, scoring, replay, and analysis are deterministic from the frozen evidence corpus. Provider generation was stochastic and is not claimed to reproduce bit-for-bit on a later API rerun.

## Evidence identities

- Completion manifest: `{analysis['completion_manifest_hash']}`
- Primary analysis: `{analysis['content_hash']}`
- Gate 2 Passport: `{passport['content_hash']}`
"""


def build_package(root: Path, output: Path, token_count_path: Path, provider_smoke_path: Path) -> dict[str, Any]:
    spec_path = root / "manifests/gate2_peer_exposure_v1.json"
    spec = load_campaign_spec(spec_path, require_certified=True)
    context = spec.context()
    paths = CampaignPaths(root / Path(*spec.artifact_root.parts))
    completion = verify_completion_manifest(context, paths)
    analysis = verify_primary_analysis(context, paths)
    token_count = read_json(token_count_path)
    verify_content_hash(token_count)
    provider_smoke = read_json(provider_smoke_path)
    verify_content_hash(provider_smoke)
    if provider_smoke.get("identity") != "NONPRODUCTION_PROVIDER_SMOKE_TEST":
        raise RuntimeError("Provider smoke-test evidence identity differs")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Result-package output directory is not empty")
    output.mkdir(parents=True, exist_ok=True)
    canonical_sources = {
        "campaign-specification.json": spec_path,
        "completion-manifest.json": paths.completion_manifest,
        "checkpoint.json": paths.checkpoint,
        "primary-analysis.json": paths.primary_analysis,
        "pre-execution-receipt.json": paths.root / "pre-execution-receipt.json",
        "execution-authorization.json": paths.root / "execution-authorization.json",
        "input-token-count.json": token_count_path,
        "provider-smoke.json": provider_smoke_path,
    }
    for name, source in canonical_sources.items():
        shutil.copyfile(source, output / name)

    provider_records = []
    replayed = 0
    for pair_id in completion["processed_pair_ids"]:
        chunk = read_json(population_path(paths, pair_id))
        if chunk["technical_validity"] == "VALID":
            replayed += 1
        for slot in chunk["slot_records"]:
            logical = str(slot["logical_slot_id"])
            request = read_json(request_path(paths, logical))
            provider_records.append(
                {
                    "logical_slot_id": logical,
                    "request_record_hash": request["content_hash"],
                    "request_content_hash": request["request_content_hash"],
                    "attempts": [
                        {
                            "attempt_number": item["attempt_number"],
                            "content_hash": item["content_hash"],
                            "provider_response_id": item["provider_response_id"],
                            "raw_provider_response_hash": item["raw_provider_response_hash"],
                            "behavioral_valid": item["behavioral_valid"],
                            "technical_error_code": item["technical_error_code"],
                        }
                        for item in attempt_results(paths, logical)
                    ],
                }
            )
    provider_index = add_content_hash(
        {
            "schema_version": "gate2-provider-evidence-index-v1",
            "campaign_id": context.campaign_id,
            "record_count": len(provider_records),
            "records": provider_records,
            "raw_corpus_location": "ignored canonical artifacts; content-addressed by this index and completion manifest",
        }
    )
    write_json(output / "provider-evidence-index.json", provider_index)
    receipt = read_json(paths.root / "pre-execution-receipt.json")
    passport = add_content_hash(
        {
            "schema_version": "gate2-passport-v1",
            "status": "VALID",
            "publication_status": "LOCAL_CANDIDATE_NOT_PUBLISHED",
            "preregistration": {
                "commit": GATE2_PREREGISTRATION_COMMIT,
                "tag": GATE2_PREREGISTRATION_TAG,
                "document_sha256": GATE2_PREREGISTRATION_SHA256,
            },
            "implementation": receipt["gate2_implementation"],
            "campaign_spec_hash": spec.spec_hash,
            "prompt_asset_hashes": dict(PROMPT_ASSET_HASHES),
            "model": MODEL_ID,
            "analyzed_populations": completion["valid_pair_count"],
            "behavioral_slots": completion["valid_behavioral_slot_count"],
            "provider_attempts": completion["provider_attempt_count"],
            "provider_accounting": analysis["exploratory"]["provider_accounting"],
            "refusal_counts": {
                condition: analysis["condition_aggregates"][condition]["refusals"]
                for condition in ("T2", "T5")
            },
            "excluded_technical_populations": completion["excluded_technical_pair_ids"],
            "completion_manifest_hash": completion["content_hash"],
            "primary_analysis_hash": analysis["content_hash"],
            "primary_decision": analysis["primary_decision"],
            "practical_magnitude_met": analysis["practical_magnitude"]["threshold_met"],
            "provider_evidence_index_hash": provider_index["content_hash"],
            "nonproduction_provider_smoke_hash": provider_smoke["content_hash"],
            "gate2_1_started": False,
            "limitations": [
                "one dated model snapshot",
                "one bounded one-step synthetic task",
                "provider generations are not bit-for-bit reproducible",
                "no topology or propagation inference",
                "no generalization to real societies or all language models",
            ],
        }
    )
    write_json(output / "gate2_passport.json", passport)
    reproducibility = add_content_hash(
        {
            "schema_version": "gate2-reproducibility-evidence-v1",
            "environment_replayed_populations": replayed,
            "environment_replay_status": "PASS",
            "completion_manifest_reconstruction": "PASS",
            "primary_analysis_reconstruction": "PASS",
            "provider_generation_reproduction_claimed": False,
            "frozen_corpus_replay": "PASS",
            "ordered_population_ensemble_hash": completion["ordered_population_ensemble_hash"],
            "ordered_request_evidence_hash": completion["ordered_request_evidence_hash"],
            "ordered_attempt_evidence_hash": completion["ordered_attempt_evidence_hash"],
        }
    )
    write_json(output / "reproducibility-evidence.json", reproducibility)
    validation = add_content_hash(
        {
            "schema_version": "gate2-result-validation-v1",
            "status": "PASS",
            "valid_populations": completion["valid_pair_count"],
            "condition_runs": completion["condition_run_count"],
            "behavioral_slots": completion["valid_behavioral_slot_count"],
            "provider_attempts": completion["provider_attempt_count"],
            "retry_attempts": analysis["exploratory"]["provider_accounting"]["retry_attempt_count"],
            "technical_invalid_populations": len(completion["excluded_technical_pair_ids"]),
            "completion_manifest_hash": completion["content_hash"],
            "analysis_hash": analysis["content_hash"],
            "analysis_run_count": analysis["analysis_run_count"],
            "gate2_1_started": False,
        }
    )
    write_json(output / "validation-report.json", validation)
    (output / "GATE_2_RESULT_REPORT.md").write_text(report_text(analysis, passport), encoding="utf-8")
    members = []
    for path in sorted(output.iterdir()):
        if path.name == "evidence-index.json" or not path.is_file():
            continue
        members.append({"path": path.name, "sha256": file_sha256(path)})
    evidence_index = add_content_hash(
        {
            "schema_version": "gate2-result-evidence-index-v1",
            "publication_status": "LOCAL_CANDIDATE_NOT_PUBLISHED",
            "members": members,
            "member_count": len(members),
            "canonical_analysis_content_hash": analysis["content_hash"],
            "canonical_completion_content_hash": completion["content_hash"],
            "provider_evidence_content_hash": provider_index["content_hash"],
        }
    )
    write_json(output / "evidence-index.json", evidence_index)
    return {
        "status": "PASS",
        "output": str(output),
        "passport_hash": passport["content_hash"],
        "evidence_index_hash": evidence_index["content_hash"],
        "report_sha256": file_sha256(output / "GATE_2_RESULT_REPORT.md"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--input-token-count", required=True)
    parser.add_argument("--provider-smoke", required=True)
    args = parser.parse_args(argv)
    result = build_package(
        Path(args.repository_root).resolve(),
        Path(args.output).resolve(),
        Path(args.input_token_count).resolve(),
        Path(args.provider_smoke).resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
