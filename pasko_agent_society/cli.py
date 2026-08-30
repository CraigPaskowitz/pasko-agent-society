"""Local command line interface for scripted Gate 1 experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .canonical import canonical_hash, to_primitive
from .experiment import (
    PopulationResult,
    ensemble_identity,
    replay_population,
    run_ensemble,
    summarize_ensemble,
)
from .fixtures import TREATMENTS, artifact_render, t2_t5_declared_difference
from .manifest import load_manifest_suite
from .schemas import ExperimentManifest


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_primitive(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _result_key(result: PopulationResult) -> tuple[str, str]:
    return result.treatment, result.replicate_id


def _manifest_by_treatment(
    manifests: Sequence[ExperimentManifest],
) -> dict[str, ExperimentManifest]:
    return {manifest.treatment: manifest for manifest in manifests}


def _reproducibility_evidence(
    manifests: Sequence[ExperimentManifest],
    primary: Sequence[PopulationResult],
    repeated: Sequence[PopulationResult],
    parallel: Sequence[PopulationResult],
) -> dict[str, Any]:
    primary_hashes = [result.result_hash for result in primary]
    repeated_hashes = [result.result_hash for result in repeated]
    parallel_hashes = [result.result_hash for result in parallel]
    manifest_lookup = _manifest_by_treatment(manifests)
    replay_checks = []
    for result in primary:
        replicate_index = int(result.replicate_id.rsplit("-", 1)[1])
        replay = replay_population(
            manifest_lookup[result.treatment], replicate_index, result.actions
        )
        replay_checks.append(
            replay["event_ledger_hash"] == result.passport.event_ledger_hash
            and replay["final_state_hash"] == result.passport.final_state_hash
            and replay["actions_hash"] == result.actions_hash
        )
    paired = {}
    by_key = {_result_key(result): result for result in primary}
    t2_count = manifest_lookup["T2"].replicate_count
    for index in range(t2_count):
        replicate_id = f"replicate-{index:03d}"
        t2 = by_key[("T2", replicate_id)]
        t5 = by_key[("T5", replicate_id)]
        paired[replicate_id] = {
            "assignment_hash_equal": (
                t2.passport.assignment_hash == t5.passport.assignment_hash
            ),
            "recorded_action_hash_equal": t2.actions_hash == t5.actions_hash,
            "environment_seed_equal": (
                t2.passport.simulator_seed == t5.passport.simulator_seed
            ),
        }
    all_paired = all(all(check.values()) for check in paired.values())
    return {
        "schema_version": "1.0.0",
        "identical_manifest_and_seed": {
            "pass": primary_hashes == repeated_hashes,
            "population_hashes_checked": len(primary_hashes),
            "first_execution_hash": ensemble_identity(primary),
            "repeat_execution_hash": ensemble_identity(repeated),
        },
        "recorded_action_replay": {
            "pass": all(replay_checks),
            "population_replays_checked": len(replay_checks),
        },
        "matched_t2_t5_randomness": {
            "pass": all_paired,
            "paired_populations_checked": len(paired),
            "declaration": (
                "T2 and T5 reuse assignment, boundary-decision, and compliant-terminal "
                "namespaces; only controlled artifact content differs."
            ),
        },
        "parallel_ordering": {
            "pass": primary_hashes == parallel_hashes,
            "population_hashes_checked": len(parallel_hashes),
            "parallel_execution_hash": ensemble_identity(parallel),
        },
        "treatment_contract": {
            "t2_t5_visible_difference_fields": list(t2_t5_declared_difference()),
            "pass": t2_t5_declared_difference() == ("peer_action",),
        },
        "overall_pass": (
            primary_hashes == repeated_hashes
            and all(replay_checks)
            and all_paired
            and primary_hashes == parallel_hashes
            and t2_t5_declared_difference() == ("peer_action",)
        ),
        "evidence_hash": canonical_hash(
            {
                "primary": primary_hashes,
                "repeated": repeated_hashes,
                "parallel": parallel_hashes,
                "replay": replay_checks,
                "paired": paired,
            }
        ),
    }


def run_command(args: argparse.Namespace) -> int:
    suite_id, manifests = load_manifest_suite(args.manifest)
    primary = run_ensemble(manifests, parallelism=args.parallelism)
    repeated = run_ensemble(manifests, parallelism=1)
    parallel = run_ensemble(manifests, parallelism=min(4, len(primary)))
    summary = summarize_ensemble(suite_id, primary)
    summary["declared_parameters"] = {
        "conditions": [manifest.treatment for manifest in manifests],
        "population_size": manifests[0].population_size,
        "replicate_populations_per_condition": manifests[0].replicate_count,
        "round_limit": 8,
        "agent_mechanism": manifests[0].agent_mechanism,
        "environment_seed": manifests[0].environment_seed,
        "assignment_seed": manifests[0].assignment_seed,
        "parameters_tuned_to_observed_result": False,
    }
    summary["result_interpretation"] = (
        "The scripted mechanism is infrastructure validation only. Any response or "
        "null response is encoded by its declared rule and is not evidence about LLM behavior."
    )
    evidence = _reproducibility_evidence(manifests, primary, repeated, parallel)
    representative = [
        to_primitive(next(result for result in primary if result.treatment == treatment).passport)
        for treatment in sorted({result.treatment for result in primary})
    ]
    output = Path(args.output)
    _write_json(output / "gate1_demo_summary.json", summary)
    _write_json(output / "reproducibility_evidence.json", evidence)
    _write_json(
        output / "representative_passports.json",
        {
            "schema_version": "1.0.0",
            "selection": "first ordered valid population from each declared treatment",
            "passports": representative,
        },
    )
    print(
        json.dumps(
            {
                "suite_id": suite_id,
                "population_runs": summary["population_runs"],
                "primary_estimand": summary["primary_estimand"],
                "reproducibility_pass": evidence["overall_pass"],
                "output": str(output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if evidence["overall_pass"] else 1


def inspect_treatments_command(_: argparse.Namespace) -> int:
    output = {}
    for treatment_id, treatment in sorted(TREATMENTS.items()):
        output[treatment_id] = {
            "task_status": treatment.task_status.value,
            "exposure_kind": treatment.exposure_kind,
            "safe_exit_salience": treatment.safe_exit_salience,
            "artifact": (
                artifact_render(treatment.artifact_content)
                if treatment.artifact_content is not None
                else None
            ),
            "artifact_length": (
                len(artifact_render(treatment.artifact_content))
                if treatment.artifact_content is not None
                else 0
            ),
        }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run synthetic Pasko Agent Society Gate 1 experiments"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run-demo", help="run and verify the scripted demo")
    run.add_argument("--manifest", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--parallelism", type=int, default=1)
    run.set_defaults(function=run_command)
    inspect_treatments = subcommands.add_parser(
        "inspect-treatments", help="render the controlled treatment fixtures"
    )
    inspect_treatments.set_defaults(function=inspect_treatments_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
