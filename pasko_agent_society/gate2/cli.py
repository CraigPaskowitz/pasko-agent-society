"""Network-free Gate 2 status, integrity, replay, and analysis CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .analysis import analyze_completed_campaign, verify_primary_analysis
from .manifest import load_campaign_spec
from .storage import (
    CampaignPaths,
    operational_status,
    publish_completion_manifest,
    verify_completion_manifest,
)


def _load(args: argparse.Namespace):
    root = Path(args.repository_root).resolve()
    spec = load_campaign_spec(root / args.manifest, require_certified=True)
    context = spec.context()
    paths = CampaignPaths(root / Path(*spec.artifact_root.parts))
    return root, spec, context, paths


def _print(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def status_command(args: argparse.Namespace) -> int:
    _, _, context, paths = _load(args)
    _print(operational_status(context, paths))
    return 0


def verify_command(args: argparse.Namespace) -> int:
    _, _, context, paths = _load(args)
    completion = publish_completion_manifest(context, paths)
    verify_completion_manifest(context, paths)
    _print(
        {
            "campaign_id": context.campaign_id,
            "valid_pairs": completion["valid_pair_count"],
            "valid_behavioral_slots": completion["valid_behavioral_slot_count"],
            "completion_manifest_hash": completion["content_hash"],
            "integrity_status": "PASS",
        }
    )
    return 0


def analyze_command(args: argparse.Namespace) -> int:
    _, _, context, paths = _load(args)
    _print(analyze_completed_campaign(context, paths))
    return 0


def verify_analysis_command(args: argparse.Namespace) -> int:
    _, _, context, paths = _load(args)
    _print(verify_primary_analysis(context, paths))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pasko Agent Society Gate 2 deterministic tools")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--manifest", default="manifests/gate2_peer_exposure_v1.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status").set_defaults(handler=status_command)
    commands.add_parser("verify").set_defaults(handler=verify_command)
    commands.add_parser("analyze").set_defaults(handler=analyze_command)
    commands.add_parser("verify-analysis").set_defaults(handler=verify_analysis_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
