"""Operator CLI for the frozen Gate 1.1 execution pipeline.

The runner never exposes a path, process, network, browser, or model capability
to simulated agents. Primary execution additionally requires a separate exact
authorization object that is intentionally absent during implementation
certification.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .gate11_analysis import analyze_primary_campaign
from .gate11_manifest import load_campaign_spec
from .gate11_storage import (
    CampaignContext,
    load_json_object,
    operational_status,
    paths_from_spec,
    publish_completion_manifest,
    run_campaign,
)


def _load(args: argparse.Namespace) -> tuple[Any, CampaignContext, Any]:
    manifest_path = Path(args.manifest).resolve()
    spec = load_campaign_spec(manifest_path, require_certified=True)
    repository_root = manifest_path.parent.parent
    context = CampaignContext.from_spec(spec)
    paths = paths_from_spec(repository_root, spec)
    return spec, context, paths


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def status_command(args: argparse.Namespace) -> int:
    _, context, paths = _load(args)
    _print(operational_status(context, paths))
    return 0


def run_command(args: argparse.Namespace) -> int:
    _, context, paths = _load(args)
    authorization = load_json_object(Path(args.authorization))
    result = run_campaign(
        context,
        paths,
        worker_count=args.workers,
        invocation_id=args.invocation_id,
        authorization=authorization,
    )
    _print(result)
    return 0 if result["integrity_status"] == "PASS" and result["invalid"] == 0 else 1


def verify_command(args: argparse.Namespace) -> int:
    _, context, paths = _load(args)
    completion = publish_completion_manifest(context, paths)
    _print(
        {
            "campaign_id": completion["campaign_id"],
            "valid_pair_count": completion["valid_pair_count"],
            "invalid_pair_count": completion["invalid_pair_count"],
            "missing_pair_count": completion["missing_pair_count"],
            "completion_manifest_hash": completion["content_hash"],
        }
    )
    return 0


def analyze_command(args: argparse.Namespace) -> int:
    _, context, paths = _load(args)
    result = analyze_primary_campaign(context, paths)
    _print(
        {
            "campaign_id": result["campaign_id"],
            "analysis_hash": result["content_hash"],
            "decision": result["decision"],
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operate the frozen local-only Gate 1.1 scripted campaign"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="show outcome-blind operational status")
    status.add_argument("--manifest", required=True)
    status.set_defaults(function=status_command)
    run = commands.add_parser("run", help="run or resume only with an exact authorization")
    run.add_argument("--manifest", required=True)
    run.add_argument("--authorization", required=True)
    run.add_argument("--workers", type=int, default=1)
    run.add_argument("--invocation-id", required=True)
    run.set_defaults(function=run_command)
    verify = commands.add_parser(
        "verify", help="publish a completion manifest only for a complete valid campaign"
    )
    verify.add_argument("--manifest", required=True)
    verify.set_defaults(function=verify_command)
    analyze = commands.add_parser(
        "analyze", help="run the locked preregistered analysis after completeness proof"
    )
    analyze.add_argument("--manifest", required=True)
    analyze.set_defaults(function=analyze_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
