"""Operational-only Gate 1.2 CLI with a suite-wide analysis lock."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .analysis import analyze_completed_suite
from .manifest import load_suite_spec
from .storage import (
    operational_status,
    paths_for_context,
    production_contexts,
    publish_completion_manifest,
    publish_suite_completion,
    read_json,
    run_subcampaign,
    suite_analysis_path,
    suite_completion_path,
    verify_suite_completion,
)


def _load(args: argparse.Namespace):
    repository_root = Path(args.repository_root).resolve()
    manifest_path = repository_root / args.manifest
    spec = load_suite_spec(manifest_path, require_certified=True)
    contexts = production_contexts(spec)
    paths_by_id = {
        context.subcampaign_id: paths_for_context(repository_root, spec, context)
        for context in contexts
    }
    return repository_root, spec, contexts, paths_by_id


def _select(contexts, selector: str):
    matches = [
        context
        for context in contexts
        if selector in {context.subcampaign_id, context.config.campaign_id, context.config.cell_id}
    ]
    if len(matches) != 1:
        raise ValueError("Selector must name exactly one frozen Gate 1.2 subcampaign or cell")
    return matches[0]


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def status_command(args: argparse.Namespace) -> int:
    _, _, contexts, paths_by_id = _load(args)
    selected = contexts if args.selector == "all" else (_select(contexts, args.selector),)
    _print(
        {
            "suite_id": contexts[0].suite_id,
            "subcampaigns": [
                operational_status(context, paths_by_id[context.subcampaign_id])
                for context in selected
            ],
        }
    )
    return 0


def run_command(args: argparse.Namespace) -> int:
    repository_root, _, contexts, paths_by_id = _load(args)
    context = _select(contexts, args.selector)
    authorization_path = repository_root / args.authorization
    authorization = read_json(authorization_path)
    _print(
        run_subcampaign(
            context,
            paths_by_id[context.subcampaign_id],
            worker_count=args.workers,
            invocation_id=args.invocation_id,
            authorization=authorization,
            authorization_contexts=contexts,
        )
    )
    return 0


def verify_subcampaign_command(args: argparse.Namespace) -> int:
    _, _, contexts, paths_by_id = _load(args)
    context = _select(contexts, args.selector)
    completion = publish_completion_manifest(context, paths_by_id[context.subcampaign_id])
    _print(
        {
            "subcampaign_id": context.subcampaign_id,
            "completion_manifest_hash": completion["content_hash"],
            "valid_unit_count": completion["valid_unit_count"],
            "integrity_status": "PASS",
        }
    )
    return 0


def verify_suite_command(args: argparse.Namespace) -> int:
    repository_root, spec, contexts, paths_by_id = _load(args)
    path = suite_completion_path(repository_root, spec)
    completion = publish_suite_completion(contexts, paths_by_id, path)
    verify_suite_completion(contexts, paths_by_id, path)
    _print(
        {
            "suite_id": completion["suite_id"],
            "completed": completion["independent_unit_count"],
            "condition_runs": completion["condition_run_count"],
            "invalid": completion["invalid_unit_count"],
            "suite_completion_hash": completion["content_hash"],
            "integrity_status": "PASS",
        }
    )
    return 0


def analyze_command(args: argparse.Namespace) -> int:
    repository_root, spec, contexts, paths_by_id = _load(args)
    result = analyze_completed_suite(
        contexts=contexts,
        paths_by_id=paths_by_id,
        suite_completion_path=suite_completion_path(repository_root, spec),
        analysis_path=suite_analysis_path(repository_root, spec),
    )
    _print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pasko Agent Society Gate 1.2")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--manifest", default="manifests/gate1_2_suite_v1.json")
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Operational counts and hashes only")
    status.add_argument("--selector", default="all")
    status.set_defaults(handler=status_command)

    run = commands.add_parser("run", help="Run one separately authorized subcampaign")
    run.add_argument("--selector", required=True)
    run.add_argument("--workers", type=int, default=1)
    run.add_argument("--invocation-id", required=True)
    run.add_argument("--authorization", required=True)
    run.set_defaults(handler=run_command)

    verify = commands.add_parser("verify-subcampaign")
    verify.add_argument("--selector", required=True)
    verify.set_defaults(handler=verify_subcampaign_command)

    verify_suite = commands.add_parser("verify-suite")
    verify_suite.set_defaults(handler=verify_suite_command)

    analyze = commands.add_parser("analyze")
    analyze.set_defaults(handler=analyze_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
