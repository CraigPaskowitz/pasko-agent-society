#!/usr/bin/env python3
"""Create the immutable Gate 2 execution authorization and zero-data receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.gate2.evidence import add_content_hash, verify_content_hash  # noqa: E402
from pasko_agent_society.gate2.manifest import load_campaign_spec  # noqa: E402
from pasko_agent_society.gate2.protocol import (  # noqa: E402
    GATE12_RESULT_COMMIT,
    GATE12_RESULT_TAG,
    GATE2_PREREGISTRATION_COMMIT,
    GATE2_PREREGISTRATION_SHA256,
    GATE2_PREREGISTRATION_TAG,
    MODEL_ID,
    PROMPT_ASSET_HASHES,
    request_byte_identity,
)
from pasko_agent_society.gate2.runner import utc_now  # noqa: E402
from pasko_agent_society.gate2.storage import CampaignPaths, atomic_write_json, read_json  # noqa: E402


def _assert_hex(value: str, length: int, label: str) -> None:
    if len(value) != length or any(character not in "0123456789abcdef" for character in value):
        raise RuntimeError(f"{label} is malformed")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--manifest", default="manifests/gate2_peer_exposure_v1.json")
    parser.add_argument("--implementation-tag", default="gate2-impl-v1")
    parser.add_argument("--implementation-tag-commit", required=True)
    parser.add_argument("--input-token-count", required=True)
    args = parser.parse_args(argv)
    root = Path(args.repository_root).resolve()
    spec = load_campaign_spec(root / args.manifest, require_certified=True)
    context = spec.context()
    _assert_hex(args.implementation_tag_commit, 40, "Implementation tag commit")
    token_record = read_json(Path(args.input_token_count))
    verify_content_hash(token_record)
    if (
        token_record.get("schema_version") != "gate2-input-token-count-v1"
        or token_record.get("campaign_spec_hash") != spec.spec_hash
        or token_record.get("production_outcome_generating_calls") != 0
    ):
        raise RuntimeError("Input-token count evidence differs from the frozen campaign")
    paths = CampaignPaths(root / Path(*spec.artifact_root.parts))
    forbidden = (
        paths.requests, paths.attempts, paths.populations, paths.checkpoint,
        paths.completion_manifest, paths.primary_analysis,
    )
    if any(path.exists() for path in forbidden):
        raise RuntimeError("Gate 2 outcome/checkpoint evidence exists before zero-data receipt")
    authorization = add_content_hash(
        {
            "schema_version": "gate2-execution-authorization-v1",
            "authorized": True,
            "campaign_id": context.campaign_id,
            "campaign_spec_hash": context.campaign_spec_hash,
            "implementation_commit": context.implementation_commit,
            "implementation_source_hash": context.implementation_source_hash,
            "preregistration_tag": GATE2_PREREGISTRATION_TAG,
            "production_model_calls_before_authorization": 0,
        }
    )
    receipt = add_content_hash(
        {
            "schema_version": "gate2-zero-data-receipt-v1",
            "recorded_at": utc_now(),
            "gate1_2_result": {"commit": GATE12_RESULT_COMMIT, "tag": GATE12_RESULT_TAG},
            "gate2_preregistration": {
                "commit": GATE2_PREREGISTRATION_COMMIT,
                "tag": GATE2_PREREGISTRATION_TAG,
                "document_sha256": GATE2_PREREGISTRATION_SHA256,
            },
            "gate2_implementation": {
                "scientific_code_commit": context.implementation_commit,
                "source_bundle_sha256": context.implementation_source_hash,
                "tag": args.implementation_tag,
                "tag_resolved_commit": args.implementation_tag_commit,
            },
            "campaign_spec_hash": context.campaign_spec_hash,
            "prompt_asset_hashes": dict(PROMPT_ASSET_HASHES),
            "request_byte_identity": request_byte_identity(root),
            "input_token_count_evidence_hash": token_record["content_hash"],
            "model": MODEL_ID,
            "primary_pair_count": 200,
            "reserve_ids": [200, 219],
            "completed_populations": 0,
            "pending_valid_populations": 200,
            "technical_invalid_populations": 0,
            "production_outcome_generating_calls": 0,
            "production_requests": 0,
            "checkpoint": None,
            "completion_manifest": None,
            "primary_analysis": None,
        }
    )
    paths.root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(paths.root / "execution-authorization.json", authorization, validator=verify_content_hash)
    atomic_write_json(paths.root / "pre-execution-receipt.json", receipt, validator=verify_content_hash)
    print(json.dumps({"status": "PASS", "authorization_hash": authorization["content_hash"], "receipt_hash": receipt["content_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
